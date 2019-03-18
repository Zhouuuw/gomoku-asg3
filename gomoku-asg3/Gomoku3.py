#from board_util import BLACK, WHITE, EMPTY
#from simple_board import SimpleGoBoard
from simple_board import SimpleGoBoard as board
from board_util import BLACK, WHITE, EMPTY


class SimulationPlayer(object):
    def __init__(self,numSim):
        self.numSim = numSim
    
    def genmove(self,board):

        result,winner = board.check_game_end_gomoku(self)
        assert not result

        simulate_moves = board.get_empty_point()
        simulate_moves_num = len(simulate_moves)
        score = [0] * simulate_moves_num
        for i in range(simulate_moves_num):
            move = simulate_moves[i]
            score[i] = self.mc_simulate(board,move)

        best_move_index = score.index(max(score))
        best_move = simulate_moves[best_move_index]
        assert best_move in simulate_moves
        return best_move

    def mc_simulate(self, board,move):
        stats = [0] * 3
        board.play(move)
        moveNr = board.moveNumber()
        for _ in range(numSim):
            winner = board.simulate()
            stats[winner] += 1
            board.resetToMoveNumber(moveNr)
        assert sum(stats) == self.numSim
        board.undo_move()
        eval = (stats[BLACK] + 0.5*stats[EMPTY]) / self.numSim
        if board.current_player == WHITE:
            eval = 1 - eval
        return eval




s = SimulationPlayer(10)
b = board
#s.genmove(b)
print('tee')

'''
def selectPlayer(numMoves,p1,p2):
    pass

def playgame(p1,p2):
    b = board
    numMoves = 0
    while not b.check_game_end_gomoku():
        player = selectPlayer(numMoves)
        b.play_move_gomoku(move)  #need color here

'''