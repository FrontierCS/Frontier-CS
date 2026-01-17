#include <iostream>

// Function to send a "move" command to the interactor.
// It prints the command to standard output and flushes.
// It then reads the interactor's response from standard input.
// Returns true if the move resulted in reaching the exit, false otherwise.
bool perform_move(int color) {
    std::cout << "move " << color << std::endl;
    int result;
    std::cin >> result;
    return result == 1;
}

// Function to send a "query" command to the interactor.
// It prints the command to standard output and flushes.
// It then reads the interactor's response (the distance) from standard input.
// Returns the current distance from the exit.
int get_distance() {
    std::cout << "query" << std::endl;
    int distance;
    std::cin >> distance;
    return distance;
}

int main() {
    // Standard competitive programming setup for faster I/O.
    // std::endl flushes the buffer, which is required for interactive problems.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int initial_deep;
    std::cin >> initial_deep;

    int current_deep = initial_deep;

    // If we start at the exit (distance 0), there's nothing to do.
    if (current_deep == 0) {
        return 0;
    }

    // The main loop continues as long as we are not at the exit.
    // Inside the loop, we are guaranteed to make one step closer to the exit.
    // The loop termination is handled by returning when perform_move indicates
    // we have reached the exit.
    while (true) {
        // At any node not at the exit, one of the three edges leads towards the
        // exit (decreasing distance), and the other two lead away (increasing distance).
        // The strategy is to test each color. If a move increases the distance,
        // we move back and try the next color. This relies on the assumption that
        // a move is its own inverse (e.g., moving "red" from A to B implies
        // moving "red" from B goes back to A), which is the simplest model
        // consistent with the problem statement.

        // Try color 0
        if (perform_move(0)) {
            // We reached the exit. The program must terminate.
            return 0;
        }

        // After moving, query the new distance to see if we got closer.
        int new_deep = get_distance();

        if (new_deep < current_deep) {
            // Success. We are one step closer. Update the current distance
            // and continue to the next step of the path.
            current_deep = new_deep;
            continue;
        } else {
            // This was the wrong direction. We must move back to the previous node.
            perform_move(0);
        }

        // Try color 1
        if (perform_move(1)) {
            return 0;
        }

        new_deep = get_distance();

        if (new_deep < current_deep) {
            current_deep = new_deep;
            continue;
        } else {
            // Wrong direction, move back.
            perform_move(1);
        }

        // If both color 0 and color 1 led away from the exit, then color 2
        // must be the one that leads towards the exit.
        if (perform_move(2)) {
            return 0;
        }
        
        // Since this must be the correct move, we know the distance has decreased by 1.
        // We can save a query by updating the distance manually.
        current_deep--;
    }

    return 0;
}