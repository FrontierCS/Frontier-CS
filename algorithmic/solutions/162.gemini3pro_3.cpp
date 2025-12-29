#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to store swap operations
struct SwapOp {
    int x1, y1, x2, y2;
};

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    const int N = 30;
    // Using a vector of vectors to represent the pyramid
    // A[x][y] stores the value at coordinates (x, y)
    vector<vector<int>> A(N);
    
    // Reading input
    for (int i = 0; i < N; ++i) {
        A[i].reserve(i + 1);
        for (int j = 0; j <= i; ++j) {
            int val;
            cin >> val;
            A[i].push_back(val);
        }
    }

    vector<SwapOp> ans;
    // Reserve memory to avoid reallocations. 
    // Theoretical max swaps is 4495 for N=30, so 10000 is safe.
    ans.reserve(10000);

    // Bottom-up heap construction strategy.
    // We iterate from the second to last row (N-2) up to the top (0).
    // The last row (N-1) does not need processing as they are leaves.
    // This order ensures that when we process a node, its children's sub-pyramids 
    // already satisfy the condition (are valid heaps).
    for (int i = N - 2; i >= 0; --i) {
        for (int j = 0; j <= i; ++j) {
            // Perform sift-down for the ball currently at (i, j)
            int curr_x = i;
            int curr_y = j;
            
            // Continue sifting down until we reach the bottom or the condition is satisfied
            while (curr_x < N - 1) {
                // Indices of the two children directly below
                int left_x = curr_x + 1;
                int left_y = curr_y;
                int right_x = curr_x + 1;
                int right_y = curr_y + 1;
                
                int val_curr = A[curr_x][curr_y];
                int val_left = A[left_x][left_y];
                int val_right = A[right_x][right_y];
                
                // Check if the heap property is satisfied: Parent < both Children
                if (val_curr < val_left && val_curr < val_right) {
                    break;
                }
                
                // If not, swap with the smaller child.
                // This is the standard greedy choice for min-heaps to float the smallest value up.
                if (val_left < val_right) {
                    // Left child is smaller, swap with left
                    ans.push_back({curr_x, curr_y, left_x, left_y});
                    swap(A[curr_x][curr_y], A[left_x][left_y]);
                    // Update current position to follow the large value down
                    curr_x = left_x;
                    curr_y = left_y;
                } else {
                    // Right child is smaller, swap with right
                    ans.push_back({curr_x, curr_y, right_x, right_y});
                    swap(A[curr_x][curr_y], A[right_x][right_y]);
                    // Update current position
                    curr_x = right_x;
                    curr_y = right_y;
                }
            }
        }
    }

    // Output result
    cout << ans.size() << "\n";
    for (const auto& op : ans) {
        cout << op.x1 << " " << op.y1 << " " << op.x2 << " " << op.y2 << "\n";
    }

    return 0;
}