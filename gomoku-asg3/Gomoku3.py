import 
class simulationPlayer():
	"""docstring for simulationPlayer"""
	def __init__(self, numSim):
		
		self.numSim = numSim

	def flat_mc_simulation(self, board,move):
		stats = [0] * 3
		board.play(move)
		moveNum = board.moveNumber() #add
		for _ in range(num):
			winner = board.simulate()
			stats[winner] += 1 
			board.resetMove(moveNum)  #add in simple_borad
 
		assert sum(stats) == self.numSim
        assert moveNum == board.moveNumber() 
        board.undoMove()
        eval = (stats[BLACK] + 0.5 * stats[EMPTY]) / self.numSim
        if board.current_player == WHITE:    #toPlay
            eval = 1 - eval
        return eval


    def genmove(self,board):
    	assert not board.check_game_end_gomoku()
    	simulate_moves = board.get_empty_point() #not 
    	simulate_moves_num = len(simulate_moves)
    	score = [0] * simulate_moves_num
    	for i in range(simulate_moves_num):
    		move = simulate_moves[i]
    		score[i] = self.simulate(board,move)

    	best_move_index = score.index(max(score))
    	best_move = simulate_moves[best_move_index]
    	assert best_move in board.get_empty_point()
    	return best_move



 



