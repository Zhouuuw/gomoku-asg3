"""
simple_board.py

Implements a basic Go board with functions to:
- initialize to a given board size
- check if a move is legal
- play a move

The board uses a 1-dimensional representation with padding
"""

import numpy as np
import random
from board_util import GoBoardUtil, BLACK, WHITE, EMPTY, BORDER, \
                       PASS, is_black_white, coord_to_point, where1d, \
                       MAXSIZE, NULLPOINT

class SimpleGoBoard(object):

    def get_color(self, point):
        return self.board[point]

    def pt(self, row, col):
        return coord_to_point(row, col, self.size)

    def is_legal(self, point, color):
        """
        Check whether it is legal for color to play on point
        """
        assert is_black_white(color)
        # Special cases
        if point == PASS:
            return True
        elif self.board[point] != EMPTY:
            return False
        if point == self.ko_recapture:
            return False
            
        # General case: detect captures, suicide
        opp_color = GoBoardUtil.opponent(color)
        self.board[point] = color
        legal = True
        has_capture = self._detect_captures(point, opp_color)
        if not has_capture and not self._stone_has_liberty(point):
            block = self._block_of(point)
            if not self._has_liberty(block): # suicide
                legal = False
        self.board[point] = EMPTY
        return legal

    def _detect_captures(self, point, opp_color):
        """
        Did move on point capture something?
        """
        for nb in self.neighbors_of_color(point, opp_color):
            if self._detect_capture(nb):
                return True
        return False

    def get_empty_points(self):
        """
        Return:
            The empty points on the board
        """
        return where1d(self.board == EMPTY)

    def __init__(self, size):
        """
        Creates a Go board of given size
        """
        assert 2 <= size <= MAXSIZE
        self.reset(size)

    def reset(self, size):
        """
        Creates a start state, an empty board with the given size
        The board is stored as a one-dimensional array
        See GoBoardUtil.coord_to_point for explanations of the array encoding
        """
        self.playout_policy = "rulebased"
        self.special_block_open_four = []
        self.special_open_four = []
        self.move_history = []
        self.size = size
        self.NS = size + 1
        self.WE = 1
        self.ko_recapture = None
        self.current_player = BLACK
        self.maxpoint = size * size + 3 * (size + 1)
        self.board = np.full(self.maxpoint, BORDER, dtype = np.int32)
        self.liberty_of = np.full(self.maxpoint, NULLPOINT, dtype = np.int32)
        self._initialize_empty_points(self.board)
        self._initialize_neighbors()
        self.transition = {
            "4C":1,
            "4O":2,

            "3C11":3,
            "3C12":3,
            "3C21":3,
            "3C22":3,
            "3C20":3,
            "3C02":3,
            "3C12":3,
            "3C22":3,

            "3O11":4,
            "3O12":4,
            "3O21":4,
            "3O22":4,
            "3O00":4,
            "3O01":4,
            "3O10":4,
            "3O02":4,
            "3O20":4

        }

    def moveNumber(self):
        return len(self.move_history)

    '''
    used in simulation 
    undo the number of move that done in simulation
    '''
    def resetToMoveNumber(self, moveNr):
        numUndos = self.moveNumber() - moveNr
        assert numUndos >= 0
        for _ in range(numUndos):
            self.undo_move()
        assert self.moveNumber() == moveNr


    def copy(self):
        b = SimpleGoBoard(self.size)
        assert b.NS == self.NS
        assert b.WE == self.WE
        b.ko_recapture = self.ko_recapture
        b.current_player = self.current_player
        assert b.maxpoint == self.maxpoint
        b.board = np.copy(self.board)
        return b

    def row_start(self, row):
        assert row >= 1
        assert row <= self.size
        return row * self.NS + 1
        
    def _initialize_empty_points(self, board):
        """
        Fills points on the board with EMPTY
        Argument
        ---------
        board: numpy array, filled with BORDER
        """
        for row in range(1, self.size + 1):
            start = self.row_start(row)
            board[start : start + self.size] = EMPTY

    def _on_board_neighbors(self, point):
        nbs = []
        for nb in self._neighbors(point):
            if self.board[nb] != BORDER:
                nbs.append(nb)
        return nbs
            
    def _initialize_neighbors(self):
        """
        precompute neighbor array.
        For each point on the board, store its list of on-the-board neighbors
        """
        self.neighbors = []
        for point in range(self.maxpoint):
            if self.board[point] == BORDER:
                self.neighbors.append([])
            else:
                self.neighbors.append(self._on_board_neighbors(point))
        
    def is_eye(self, point, color):
        """
        Check if point is a simple eye for color
        """
        if not self._is_surrounded(point, color):
            return False
        # Eye-like shape. Check diagonals to detect false eye
        opp_color = GoBoardUtil.opponent(color)
        false_count = 0
        at_edge = 0
        for d in self._diag_neighbors(point):
            if self.board[d] == BORDER:
                at_edge = 1
            elif self.board[d] == opp_color:
                false_count += 1
        return false_count <= 1 - at_edge # 0 at edge, 1 in center
    
    def _is_surrounded(self, point, color):
        """
        check whether empty point is surrounded by stones of color.
        """
        for nb in self.neighbors[point]:
            nb_color = self.board[nb]
            if nb_color != color:
                return False
        return True

    def _stone_has_liberty(self, stone):
        lib = self.find_neighbor_of_color(stone, EMPTY)
        return lib != None

    def _get_liberty(self, block):
        """
        Find any liberty of the given block.
        Returns None in case there is no liberty.
        block is a numpy boolean array
        """
        for stone in where1d(block):
            lib = self.find_neighbor_of_color(stone, EMPTY)
            if lib != None:
                return lib
        return None

    def _has_liberty(self, block):
        """
        Check if the given block has any liberty.
        Also updates the liberty_of array.
        block is a numpy boolean array
        """
        lib = self._get_liberty(block)
        if lib != None:
            assert self.get_color(lib) == EMPTY
            for stone in where1d(block):
                self.liberty_of[stone] = lib
            return True
        return False

    def _block_of(self, stone):
        """
        Find the block of given stone
        Returns a board of boolean markers which are set for
        all the points in the block 
        """
        marker = np.full(self.maxpoint, False, dtype = bool)
        pointstack = [stone]
        color = self.get_color(stone)
        assert is_black_white(color)
        marker[stone] = True
        while pointstack:
            p = pointstack.pop()
            neighbors = self.neighbors_of_color(p, color)
            for nb in neighbors:
                if not marker[nb]:
                    marker[nb] = True
                    pointstack.append(nb)
        return marker

    def _fast_liberty_check(self, nb_point):
        lib = self.liberty_of[nb_point]
        if lib != NULLPOINT and self.get_color(lib) == EMPTY:
            return True # quick exit, block has a liberty  
        if self._stone_has_liberty(nb_point):
            return True # quick exit, no need to look at whole block
        return False
        
    def _detect_capture(self, nb_point):
        """
        Check whether opponent block on nb_point is captured.
        Returns boolean.
        """
        if self._fast_liberty_check(nb_point):
            return False
        opp_block = self._block_of(nb_point)
        return not self._has_liberty(opp_block)
    
    def _detect_and_process_capture(self, nb_point):
        """
        Check whether opponent block on nb_point is captured.
        If yes, remove the stones.
        Returns the stone if only a single stone was captured,
            and returns None otherwise.
        This result is used in play_move to check for possible ko
        """
        if self._fast_liberty_check(nb_point):
            return None
        opp_block = self._block_of(nb_point)
        if self._has_liberty(opp_block):
            return None
        captures = list(where1d(opp_block))
        self.board[captures] = EMPTY
        self.liberty_of[captures] = NULLPOINT
        single_capture = None 
        if len(captures) == 1:
            single_capture = nb_point
        return single_capture

    def play_move(self, point, color):
        """
        Play a move of color on point
        Returns boolean: whether move was legal
        """
        assert is_black_white(color)
        # Special cases
        if point == PASS:
            self.ko_recapture = None
            self.current_player = GoBoardUtil.opponent(color)
            return True
        elif self.board[point] != EMPTY:
            return False
        if point == self.ko_recapture:
            return False
            
        # General case: deal with captures, suicide, and next ko point
        opp_color = GoBoardUtil.opponent(color)
        in_enemy_eye = self._is_surrounded(point, opp_color)
        self.board[point] = color
        single_captures = []
        neighbors = self.neighbors[point]
        for nb in neighbors:
            if self.board[nb] == opp_color:
                single_capture = self._detect_and_process_capture(nb)
                if single_capture != None:
                    single_captures.append(single_capture)
        if not self._stone_has_liberty(point):
            # check suicide of whole block
            block = self._block_of(point)
            if not self._has_liberty(block): # undo suicide move
                self.board[point] = EMPTY
                return False
        self.ko_recapture = None
        if in_enemy_eye and len(single_captures) == 1:
            self.ko_recapture = single_captures[0]
        self.current_player = GoBoardUtil.opponent(color)
        return True

    def neighbors_of_color(self, point, color):
        """ List of neighbors of point of given color """
        nbc = []
        for nb in self.neighbors[point]:
            if self.get_color(nb) == color:
                nbc.append(nb)
        return nbc
        
    def find_neighbor_of_color(self, point, color):
        """ Return one neighbor of point of given color, or None """
        for nb in self.neighbors[point]:
            if self.get_color(nb) == color:
                return nb
        return None
        
    def _neighbors(self, point):
        """ List of all four neighbors of the point """
        return [point - 1, point + 1, point - self.NS, point + self.NS]

    def _diag_neighbors(self, point):
        """ List of all four diagonal neighbors of point """
        return [point - self.NS - 1, 
                point - self.NS + 1, 
                point + self.NS - 1, 
                point + self.NS + 1]
    
    def _point_to_coord(self, point):
        """
        Transform point index to row, col.
        
        Arguments
        ---------
        point
        
        Returns
        -------
        x , y : int
        coordination of the board  1<= x <=size, 1<= y <=size .
        """
        if point is None:
            return 'pass'
        row, col = divmod(point, self.NS)
        return row, col

    def is_legal_gomoku(self, point, color):
        """
            Check whether it is legal for color to play on point, for the game of gomoku
            """
        return self.board[point] == EMPTY
    
    def undo_move(self):
        point = self.move_history.pop()
        opponent_color = GoBoardUtil.opponent(self.current_player)
        assert self.get_color(point) == opponent_color
        self.board[point] = EMPTY
        self.current_player = opponent_color

    def play_move_gomoku(self, point, color):
        """
            Play a move of color on point, for the game of gomoku
            Returns boolean: whether move was legal
            """
        assert is_black_white(color)
        assert point != PASS
        if self.board[point] != EMPTY:
            return False
        self.board[point] = color
        self.current_player = GoBoardUtil.opponent(color)
        self.move_history.append(point)
        return True
        
    def _point_direction_check_connect_gomoko(self, point, shift):
        """
        Check if the point has connect5 condition in a direction
        for the game of Gomoko.
        """
        color = self.board[point]
        count = 1
        d = shift
        p = point
        while True:
            p = p + d
            if self.board[p] == color:
                count = count + 1
                if count == 5:
                    break
            else:
                break
        d = -d
        p = point
        while True:
            p = p + d
            if self.board[p] == color:
                count = count + 1
                if count == 5:
                    break
            else:
                break
        assert count <= 5
        return count == 5
    
    def point_check_game_end_gomoku(self, point):
        """
            Check if the point causes the game end for the game of Gomoko.
            """
        # check horizontal
        if self._point_direction_check_connect_gomoko(point, 1):
            return True
        
        # check vertical
        if self._point_direction_check_connect_gomoko(point, self.NS):
            return True
        
        # check y=x
        if self._point_direction_check_connect_gomoko(point, self.NS + 1):
            return True
        
        # check y=-x
        if self._point_direction_check_connect_gomoko(point, self.NS - 1):
            return True
        
        return False
    
    def check_game_end_gomoku(self):
        """
            Check if the game ends for the game of Gomoku.
            """
        white_points = where1d(self.board == WHITE)
        black_points = where1d(self.board == BLACK)
        
        for point in white_points:
            if self.point_check_game_end_gomoku(point):
                return True, WHITE
    
        for point in black_points:
            if self.point_check_game_end_gomoku(point):
                return True, BLACK

        return False, None

    def check_from_one_direction(self,point,d):
        """
        For any given empty point on given shifting position,
        check the number of blacks or whites on positive and negative diretion
        and the number of empty after blacks or white.
        Get the maxmum number of whites or blacks and record the color

        """
        p = point + d
        positive_BW= 0
        positive_empty = 0
        c1 = self.get_color(p)
        if c1 == BLACK or c1 == WHITE:
            while self.get_color(p) == c1:
                positive_BW+=1
                p += d
            if positive_BW == 4:
                return("4"+self.get_O_or_C(c1))
            while self.get_color(p) == EMPTY and positive_empty< 2:
                positive_empty+= 1
                p += d
        elif c1 == EMPTY:
            while positive_empty< 2 and self.get_color(p) == EMPTY:
                positive_empty+= 1
                p += d

        p = point - d
        negative_BW= 0
        negative_empty= 0
        c2 = self.get_color(p)
        if c2 == BLACK or c2 == WHITE:
            while self.get_color(p) == c2:
                negative_BW +=1
                p -= d
            if negative_BW == 4:
                return("4"+self.get_O_or_C(c2))
            while self.get_color(p) == EMPTY and negative_empty < 2:
                negative_empty += 1
                p -= d
        elif c2 == EMPTY:
            while negative_empty < 2 and self.get_color(p) == EMPTY:
                negative_empty += 1
                p -= d

        
        if c1==EMPTY and c2!=EMPTY:
            return(str(negative_BW)+self.get_O_or_C(c2)+str(positive_empty)+str(negative_empty))
        elif c1!=EMPTY and c2==EMPTY:
            return(str(positive_BW)+self.get_O_or_C(c1)+str(positive_empty)+str(negative_empty))
        elif c1 == EMPTY and c2 == EMPTY:
            return(str(0)+str(EMPTY)+str(positive_empty)+str(negative_empty))
        else:
            if c1 == c2:
                return(str(positive_BW + negative_BW)+self.get_O_or_C(c1)+str(positive_empty)+str(negative_empty))
            else:
                if positive_BW >= negative_BW:
                    return(str(positive_BW)+self.get_O_or_C(c1)+str(positive_empty)+str(negative_empty))
                else:
                    return(str(negative_BW)+self.get_O_or_C(c2)+str(positive_empty)+str(negative_empty))

    def get_O_or_C(self,c):
        """
        return string code c for current player, o for opponent player
        """
        if c == self.current_player:
            return "C"
        else:
            return "O"

    def evaluate_empty_point(self,point):
        """
        win get a priority 1
        BlockWin get a priority 2
        OpenFour get a priority 3
        BlockOpenFourget a priority 4
        """
        shifts = [1,self.NS,-self.NS,self.NS+1,self.NS-1]
        priority = []
        for shift in shifts:
            code = self.check_from_one_direction(point,shift)
            if code in self.transition:
                if code == "3O21" or code == "3022":
                    self.special_block_open_four.append(point + shift)
                if code == "3C20" or code == "3C21" or code == "3C22":
                    if self.get_color(point+shift) == 0:
                        self.special_open_four.append(point+shift)
                if code == "3O02" or code == "3C12" or code == "3C22":
                    if self.get_color(point-shift) == 0:
                        self.special_open_four.append(point-shift)
                priority.append(self.transition[code])
        if len(priority) != 0:
            priority.sort()
            return priority[0]
        return 5

    def simulate(self):
        """
        1. check if any player win first
        2. if no player wins, copy current board into b
        and play all legal moves in a random order
        until there is a win or a draw.
        3. Finally return simulate result for sampling
        """
        result,winner = self.check_game_end_gomoku()
        if result == True:
            return winner

        all_moves = self.get_empty_points()
        random.shuffle(all_moves)
        b = self.copy()
        for i in range(len(all_moves)):
            b.play_move_gomoku(all_moves[i],b.current_player)
            result,winner = b.check_game_end_gomoku()
            if result == True:
                return winner
        return 0

    def legal_move_around_stone_blocks(self):

        legal_move = []
        empty_point = self.get_empty_points()

        if len(empty_point) < self.size:
            legal_move = empty_point

        elif len(empty_point) == self.size * self.size:
            return empty_point

        else:
            black_points=where1d(self.board == BLACK).tolist()
            white_points=where1d(self.board == WHITE).tolist()
            not_empty_points = black_points + white_points

            checking_set = set()

            for point in not_empty_points:
                checking_set.update(self._neighbors(point))
                checking_set.update(self._diag_neighbors(point))
            
            for point in checking_set:
                if self.get_color(point) == EMPTY:
                    legal_move.append(point)

        print("legal_move is "+str(legal_move))
        value = []
        d = {}
        for key in legal_move:
            v=self.evaluate_empty_point(key)
            value.append(v)
            d[key] = v
        print("value is" +str(value))
        sorted_value = sorted(d.items(),reverse = True,key = lambda kv:kv[1])

        sorted_legal_move = []
        for t in sorted_value:
            sorted_legal_move.append(t[0])

        return legal_move

    def set_playout_policy(self,policy):
        self.playout_policy = policy
            

