#include <iostream>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int initial_deep;
    std::cin >> initial_deep;

    if (initial_deep == 0) {
        return 0;
    }

    int current_deep = initial_deep;
    int last_up_color = -1;
    int reached_exit_flag;

    while (current_deep > 0) {
        int up_color = -1;

        if (last_up_color == -1) {
            // First step: no information on which way is down. Test up to two colors.
            // Test color 0
            std::cout << "move 0" << std::endl;
            std::cin >> reached_exit_flag;
            if (reached_exit_flag) return 0;
            
            std::cout << "query" << std::endl;
            int new_deep;
            std::cin >> new_deep;
            
            std::cout << "move 0" << std::endl; // Move back
            std::cin >> reached_exit_flag;
            
            if (new_deep < current_deep) {
                up_color = 0;
            } else {
                // Test color 1
                std::cout << "move 1" << std::endl;
                std::cin >> reached_exit_flag;
                if (reached_exit_flag) return 0;

                std::cout << "query" << std::endl;
                std::cin >> new_deep;
                
                std::cout << "move 1" << std::endl; // Move back
                std::cin >> reached_exit_flag;

                if (new_deep < current_deep) {
                    up_color = 1;
                } else {
                    up_color = 2;
                }
            }
        } else {
            // Subsequent steps: we know `last_up_color` leads down. Test one of the other two.
            int c1 = (last_up_color + 1) % 3;
            int c2 = (last_up_color + 2) % 3;
            
            // Test c1
            std::cout << "move " << c1 << std::endl;
            std::cin >> reached_exit_flag;
            if (reached_exit_flag) return 0;

            std::cout << "query" << std::endl;
            int new_deep;
            std::cin >> new_deep;

            std::cout << "move " << c1 << std::endl; // Move back
            std::cin >> reached_exit_flag;

            if (new_deep < current_deep) {
                up_color = c1;
            } else {
                up_color = c2;
            }
        }
        
        // Make the final move for this level
        std::cout << "move " << up_color << std::endl;
        std::cin >> reached_exit_flag;
        if (reached_exit_flag) {
            return 0;
        }

        current_deep--;
        last_up_color = up_color;
    }

    return 0;
}