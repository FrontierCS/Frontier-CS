#include <iostream>

// Helper function to interact with the system by moving.
// It sends the move command and returns the interactor's response.
int do_move(int c) {
    std::cout << "move " << c << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Helper function to query the current distance to the exit.
int do_query() {
    std::cout << "query" << std::endl;
    int dist;
    std::cin >> dist;
    return dist;
}

int main() {
    // Fast I/O for competitive programming
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int initialDeep;
    std::cin >> initialDeep;

    int current_d = initialDeep;

    // If we start at the exit, we are done.
    if (current_d == 0) {
        return 0;
    }

    int color_from_prev;

    // --- First step ---
    // At the beginning, we have no information. We test colors 0 and 1.
    // If both lead down, color 2 must be the way up.
    int up_color = -1;
    for (int c = 0; c < 2; ++c) {
        if (do_move(c) == 1) {
            return 0;
        }
        int d_new = do_query();
        if (d_new < current_d) {
            up_color = c;
            break;
        }
        do_move(c); // Move back
    }

    if (up_color == -1) {
        up_color = 2;
        if (do_move(up_color) == 1) {
            return 0;
        }
    }
    
    current_d--;
    color_from_prev = up_color;

    // --- Subsequent steps ---
    // For every step after the first, we know the color of the edge we just used.
    // This color leads "down", so we only need to test the other two colors.
    while (current_d > 0) {
        // Determine the other two colors to test using modulo arithmetic
        int c1 = (color_from_prev + 1) % 3;
        int c2 = (color_from_prev + 2) % 3;
        
        // Test the first candidate color
        if (do_move(c1) == 1) {
            return 0;
        }
        int d_new = do_query();

        if (d_new < current_d) {
            // c1 is the "up" color
            up_color = c1;
        } else {
            // c1 leads "down", so move back.
            do_move(c1);
            // By elimination, c2 must be the "up" color.
            up_color = c2;
            if (do_move(up_color) == 1) {
                return 0;
            }
        }

        current_d--;
        color_from_prev = up_color;
    }

    return 0;
}