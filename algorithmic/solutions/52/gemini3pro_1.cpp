#include <iostream>
#include <vector>

using namespace std;

// Function to query the number of value-contiguous segments in the range [l, r]
int query_segments(int l, int r) {
    if (l > r) return 0;
    cout << "1 " << l << " " << r << endl;
    int x;
    cin >> x;
    return x;
}

// Function to swap elements at positions i and j
void perform_swap(int i, int j) {
    if (i == j) return;
    cout << "2 " << i << " " << j << endl;
    int x;
    cin >> x;
}

int main() {
    // Optimize I/O operations, though flush is handled by endl
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n, l1, l2;
    if (!(cin >> n >> l1 >> l2)) return 0;

    // current_len represents the length of the prefix p[1...current_len]
    // which forms a value-contiguous chain (e.g., values x, x+1, x+2...).
    int current_len = 1;

    while (current_len < n) {
        // Check if the current end of the chain (p[current_len]) has a neighbor (value-wise)
        // in the remaining unknown part of the array p[current_len+1 ... n].
        // The number of segments in [current_len, n] will be equal to or less than 
        // the number of segments in [current_len+1, n] if p[current_len] connects to something in the rest.
        int q_total = query_segments(current_len, n);
        int q_rest = query_segments(current_len + 1, n);

        if (q_total <= q_rest) {
            // A neighbor exists in p[current_len+1 ... n].
            // Use binary search to find its exact index.
            int L = current_len + 1;
            int R = n;
            
            while (L < R) {
                int mid = L + (R - L) / 2;
                // Check if the neighbor is in the left half [current_len+1, mid]
                int q_sub_total = query_segments(current_len, mid);
                int q_sub_rest = query_segments(current_len + 1, mid);
                
                if (q_sub_total <= q_sub_rest) {
                    R = mid; // Neighbor is in the left half
                } else {
                    L = mid + 1; // Neighbor is in the right half
                }
            }
            // L is the index of the neighbor. Move it to the next position in the chain.
            perform_swap(current_len + 1, L);
            current_len++;
        } else {
            // No neighbor found in the rest. This implies p[current_len] is an endpoint (value 1 or n).
            // We reverse the currently known chain p[1...current_len] so that the other end
            // (which must have a neighbor in the rest) is now at p[current_len].
            for (int i = 1; i <= current_len / 2; ++i) {
                perform_swap(i, current_len - i + 1);
            }
            // Continue the loop; the next iteration will find a neighbor.
        }
    }

    // Output the final permutation.
    // Since we constructed a chain of length n, the array contains either 1...n or n...1.
    // The problem states we just need to find one of the possible permutations.
    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << i;
    }
    cout << endl;

    return 0;
}