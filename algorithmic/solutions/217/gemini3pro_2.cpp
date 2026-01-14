#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global variables to store problem state
int N, M;

// Global available items for the current pass (values)
vector<int> current_U;
// Current stick being built (values)
vector<int> current_S;
// Mask to mark items in current_U that are currently in current_S
vector<bool> is_in_S;
// Current pass number (number of sticks remaining in current_U)
int current_k;

// Interactor function
int query(const vector<int>& subset) {
    if (subset.empty()) return 0;
    cout << "? " << subset.size();
    for (int x : subset) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Function to output a stick
void answer(const vector<int>& stick) {
    cout << "! ";
    for (size_t i = 0; i < stick.size(); ++i) {
        cout << stick[i] << (i == stick.size() - 1 ? "" : " ");
    }
    cout << endl;
}

// Checks if the range [start_idx, start_idx + len - 1] in current_U
// contains at least one "good" item. A "good" item is one whose color
// is NOT currently present in current_S.
bool contains_good(int start_idx, int len) {
    if (len <= 0) return false;

    // We query the Universe excluding (S U T).
    // The "Universe" is the set of all currently available dangos (current_U).
    // T is the subset current_U[start_idx ... start_idx + len - 1].
    // S is marked by is_in_S.

    // If removing (S U T) drops the max sticks count to current_k - 1,
    // it means T did not introduce any NEW conflicts (duplicates) that weren't already in S.
    // Wait, the logic is:
    // If T contains at least one GOOD item (color not in S):
    //   Removing that item reduces the count of that color to k-1.
    //   Removing S does not affect that color (since not in S).
    //   So the minimum color count becomes k-1. Result is k-1.
    // If T contains ONLY BAD items (all colors in S):
    //   For every c in T, c is in S.
    //   Removing S reduces count of c to k-1.
    //   Removing T reduces count of c further (>= 1 copy in T).
    //   So count becomes <= k-2.
    //   Result <= k-2.
    
    // So: Result == k-1 implies at least one good item.

    vector<int> q_subset;
    q_subset.reserve(current_U.size());

    for (size_t i = 0; i < current_U.size(); ++i) {
        // Exclude items in S
        if (is_in_S[i]) continue;
        // Exclude items in T
        if ((int)i >= start_idx && (int)i < start_idx + len) continue;
        
        q_subset.push_back(current_U[i]);
    }

    int res = query(q_subset);
    return res == current_k - 1;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    
    if (!(cin >> N >> M)) return 0;

    // Initial universe contains all dangos
    vector<int> U(N * M);
    iota(U.begin(), U.end(), 1);

    // We process sticks from M down to 2.
    // The last stick (1) is whatever remains.
    for (int k = M; k >= 2; --k) {
        current_k = k;
        current_U = U;
        current_S.clear();
        current_S.reserve(N);
        is_in_S.assign(current_U.size(), false);
        
        vector<int> next_U_indices; // Indices of items to keep for next pass
        next_U_indices.reserve(current_U.size() - N);
        
        int cursor = 0;
        int U_size = current_U.size();
        int step = 1;

        // Iterate through current_U to fill current_S
        while (current_S.size() < N && cursor < U_size) {
            // Determine length of block to check
            int len = std::min(step, U_size - cursor);
            
            if (contains_good(cursor, len)) {
                // The range [cursor, cursor+len-1] contains at least one good item.
                // Binary search to find the FIRST good item in this range.
                int low = 0; 
                int high = len - 1;
                int first_good_offset = high;

                while (low <= high) {
                    int mid = low + (high - low) / 2;
                    // Check if prefix [0...mid] of the block has a good item
                    if (contains_good(cursor, mid + 1)) {
                        first_good_offset = mid;
                        high = mid - 1;
                    } else {
                        low = mid + 1;
                    }
                }

                // Items before the first good one are bad -> move to next_U
                for (int i = 0; i < first_good_offset; ++i) {
                    next_U_indices.push_back(cursor + i);
                }

                // Add the good item to S
                int good_idx = cursor + first_good_offset;
                current_S.push_back(current_U[good_idx]);
                is_in_S[good_idx] = true;

                // Advance cursor past the good item
                cursor += first_good_offset + 1;
                
                // Reset step size since we found a good item (density might change)
                step = 1;
            } else {
                // The entire block contains only bad items.
                // Discard all of them.
                for (int i = 0; i < len; ++i) {
                    next_U_indices.push_back(cursor + i);
                }
                cursor += len;
                // Exponentially increase step size to skip larger blocks of bad items
                step *= 2;
            }
        }

        // Add any remaining unprocessed items to next_U
        for (; cursor < U_size; ++cursor) {
            next_U_indices.push_back(cursor);
        }

        // Output the found stick
        answer(current_S);

        // Prepare universe for the next pass
        vector<int> next_U_vec;
        next_U_vec.reserve(next_U_indices.size());
        for (int idx : next_U_indices) {
            next_U_vec.push_back(current_U[idx]);
        }
        U = next_U_vec;
    }

    // Output the last remaining stick
    answer(U);

    return 0;
}