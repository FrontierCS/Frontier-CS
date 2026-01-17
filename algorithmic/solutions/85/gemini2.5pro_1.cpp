#include <iostream>

/**
 * Solves the interactive Maze problem.
 * 
 * The strategy is to iteratively find the edge that leads closer to the exit (the "up" edge)
 * and move along it, until the exit is reached.
 * 
 * At any node at a distance `d > 0` from the exit, there are three edges. One leads to a node
 * at distance `d-1` ("up"), and two lead to nodes at distance `d+1` ("down").
 * 
 * To find the "up" edge, we test the edges one by one. The colors are 0, 1, 2.
 * 1. Try moving along edge 0.
 * 2. Query the new distance.
 * 3. If the distance decreased, we found the "up" edge. We are now one step closer.
 * 4. If the distance increased, it was a "down" edge. We move back along edge 0 to our
 *    original position and try the next color.
 * 5. We repeat this for color 1.
 * 6. If both 0 and 1 were "down" edges, we can deduce that color 2 must be the "up" edge,
 *    so we can move along it without needing a final query to confirm.
 * 
 * This process is repeated until the exit is reached. The program terminates as soon as a
 * move results in reaching the exit.
 * 
 * Cost analysis per step (to get one level closer):
 * - Best case (color 0 is 'up'): 1 move, 1 query.
 * - Middle case (color 1 is 'up'): 3 moves (0 down, 0 back, 1 up), 2 queries.
 * - Worst case (color 2 is 'up'): 5 moves (0 down, 0 back, 1 down, 1 back, 2 up), 2 queries.
 * 
 * With an initial distance of up to 10^4, the total operations are well within the given
 * limits of 10^5 moves and 10^5 queries.
 */
void solve() {
    long long current_deep;
    std::cin >> current_deep;

    while (current_deep > 0) {
        bool found_up = false;

        // Try colors 0 and 1
        for (int c = 0; c < 2; ++c) {
            // Make a test move
            std::cout << "move " << c << std::endl;
            int is_exit;
            std::cin >> is_exit;
            if (is_exit) {
                return;
            }

            // Check the result of the move
            std::cout << "query" << std::endl;
            long long new_deep;
            std::cin >> new_deep;

            if (new_deep < current_deep) {
                // Successful move towards the exit
                current_deep = new_deep;
                found_up = true;
                break;
            } else {
                // It was a move away from the exit, so move back
                std::cout << "move " << c << std::endl;
                std::cin >> is_exit; // Must read the result, which will be 0.
            }
        }

        if (found_up) {
            continue;
        }

        // If we are here, colors 0 and 1 were 'down' moves. Color 2 must be the 'up' move.
        std::cout << "move 2" << std::endl;
        int is_exit;
        std::cin >> is_exit;
        if (is_exit) {
            return;
        }
        
        // We know the distance decreased by 1 without needing another query.
        current_deep--;
    }
}

int main() {
    // For interactive problems, it's generally better to not use fast I/O
    // as it can sometimes interfere with the judge's I/O handling.
    // The `std::endl` manipulator ensures the output is flushed after each command.
    solve();
    return 0;
}