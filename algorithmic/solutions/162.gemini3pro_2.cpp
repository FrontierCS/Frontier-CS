#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to store swap operations
struct Move {
    int x1, y1, x2, y2;
};

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N = 30;
    vector<vector<int>> b(N);
    
    // Reading input: constructing the pyramid
    for (int i = 0; i < N; ++i) {
        b[i].resize(i + 1);
        for (int j = 0; j <= i; ++j) {
            cin >> b[i][j];
        }
    }

    vector<Move> moves;
    
    // We apply a bottom-up heap construction strategy.
    // We iterate from the second-to-last row up to the top row (0).
    // For each ball, we "sift it down" if it violates the heap property (i.e., if it is larger than one of its children).
    // By processing bottom-up, we ensure that when we are at row `i`, the sub-pyramids starting at row `i+1`
    // already satisfy the heap property internally. Sifting down might disturb them, but the recursive nature
    // of the sift-down (while loop) fixes any new violations introduced deeper in the pyramid.
    
    for (int i = N - 2; i >= 0; --i) {
        for (int j = 0; j <= i; ++j) {
            int curr_x = i;
            int curr_y = j;
            
            // Sift down the element currently at (curr_x, curr_y)
            while (curr_x < N - 1) {
                int val = b[curr_x][curr_y];
                // The two children of (x, y) are (x+1, y) and (x+1, y+1)
                int child1 = b[curr_x + 1][curr_y];
                int child2 = b[curr_x + 1][curr_y + 1];
                
                // If the current value is smaller than both children, the condition is satisfied locally.
                if (val < child1 && val < child2) {
                    break;
                }
                
                // If not, we must swap with the smaller of the two children.
                // Swapping with the smaller child ensures that the new parent (which was the smaller child)
                // is smaller than the other child.
                int swap_x = curr_x + 1;
                int swap_y;
                
                if (child1 < child2) {
                    swap_y = curr_y;
                } else {
                    swap_y = curr_y + 1;
                }
                
                // Record the swap
                moves.push_back({curr_x, curr_y, swap_x, swap_y});
                
                // Perform the swap in the grid
                swap(b[curr_x][curr_y], b[swap_x][swap_y]);
                
                // Move down to the child's position and continue checking
                curr_x = swap_x;
                curr_y = swap_y;
            }
        }
    }

    // Output the number of operations and the operations themselves
    cout << moves.size() << "\n";
    for (const auto& m : moves) {
        cout << m.x1 << " " << m.y1 << " " << m.x2 << " " << m.y2 << "\n";
    }

    return 0;
}