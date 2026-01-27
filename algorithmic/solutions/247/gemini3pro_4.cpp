#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

struct Op {
    int i, j;
};

int N;
vector<int> A, B;
vector<Op> ops;

// Apply operation on 0-based indices i, j (i < j)
// Updates global A and records operation
void apply_op(int i, int j) {
    ops.push_back({i + 1, j + 1});
    int val_i = A[i];
    int val_j = A[j];
    A[i] = val_j - 1;
    A[j] = val_i + 1;
}

// Calculate cost as sum of absolute differences between sorted X and sorted Y
// X[i] = A[i] - (i + 1)
long long calculate_cost(const vector<int>& current_A) {
    vector<int> X(N), Y(N);
    for (int i = 0; i < N; ++i) {
        X[i] = current_A[i] - (i + 1);
        Y[i] = B[i] - (i + 1);
    }
    sort(X.begin(), X.end());
    sort(Y.begin(), Y.end());
    long long cost = 0;
    for (int i = 0; i < N; ++i) {
        cost += abs(X[i] - Y[i]);
    }
    return cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    A.resize(N);
    B.resize(N);
    long long sumA = 0, sumB = 0;
    for (int i = 0; i < N; ++i) {
        cin >> A[i];
        sumA += A[i];
    }
    for (int i = 0; i < N; ++i) {
        cin >> B[i];
        sumB += B[i];
    }

    if (sumA != sumB) {
        cout << "No" << endl;
        return 0;
    }

    // Phase 1: Match multisets of X-values
    while (true) {
        long long current_cost = calculate_cost(A);
        if (current_cost == 0) break;

        long long best_cost = current_cost;
        int best_i = -1, best_j = -1;

        // Try all non-adjacent operations to see if we can reduce cost
        for (int i = 0; i < N; ++i) {
            for (int j = i + 2; j < N; ++j) { // gap >= 1
                int old_Ai = A[i];
                int old_Aj = A[j];
                
                A[i] = old_Aj - 1;
                A[j] = old_Ai + 1;
                
                long long new_cost = calculate_cost(A);
                if (new_cost < best_cost) {
                    best_cost = new_cost;
                    best_i = i;
                    best_j = j;
                }
                
                A[i] = old_Ai;
                A[j] = old_Aj;
            }
        }

        if (best_i != -1) {
            apply_op(best_i, best_j);
        } else {
            // No direct improvement found. 
            // We need to move items to adjust the gap between a surplus and a deficit.
            vector<int> X(N), Y(N);
            vector<pair<int, int>> sorted_X(N);
            for (int i = 0; i < N; ++i) {
                X[i] = A[i] - (i + 1);
                sorted_X[i] = {X[i], i};
                Y[i] = B[i] - (i + 1);
            }
            sort(Y.begin(), Y.end());
            sort(sorted_X.begin(), sorted_X.end());

            // Find best pair of items (indices in sorted_X) to fix
            int best_k = -1, best_l = -1;
            int max_Dk = -1; 
            int min_Dl = 1;

            // X[p] > Y[p]: needs decrease (move right)
            // X[p] < Y[p]: needs increase (move left)
            for(int k=0; k<N; ++k) {
                int diff = sorted_X[k].first - Y[k];
                if (diff > 0) {
                    if (diff > max_Dk) {
                        max_Dk = diff;
                        best_k = k;
                    }
                }
            }
            for(int l=0; l<N; ++l) {
                int diff = sorted_X[l].first - Y[l];
                if (diff < 0) {
                     if (diff < min_Dl) {
                        min_Dl = diff;
                        best_l = l;
                    }
                }
            }

            if (best_k != -1 && best_l != -1) {
                int u = sorted_X[best_k].second; // has surplus
                int v = sorted_X[best_l].second; // has deficit
                
                // We want to apply op(u, v) with u < v to transfer from u to v.
                if (u > v) {
                    // Need to swap order
                    apply_op(u - 1, u);
                } else {
                    // u < v. Check distance.
                    int desired_transfer = min(max_Dk, -min_Dl); 
                    int current_gap = v - u - 1;
                    
                    if (current_gap > desired_transfer) {
                        // Too far, move v closer
                        apply_op(v - 1, v);
                    } else if (current_gap < desired_transfer) {
                        // Too close, move apart
                        if (v < N - 1) apply_op(v, v + 1);
                        else if (u > 0) apply_op(u - 1, u);
                        else {
                            // Can't expand, just swap to change state
                             apply_op(u, u+1);
                        }
                    } else {
                         // Gap is perfect but wasn't picked (maybe didn't reduce global cost?)
                         // Force it to progress.
                         apply_op(u, v);
                    }
                }
            } else {
                // Should not happen if cost > 0
                break;
            }
        }
    }
    
    // Phase 2: Permutation match (Bubble Sort)
    // Map current items to target slots based on sorted order matching
    vector<int> X(N), Y(N);
    for (int i = 0; i < N; ++i) {
        X[i] = A[i] - (i + 1);
        Y[i] = B[i] - (i + 1);
    }
    
    vector<pair<int, int>> curr_items(N); 
    for(int i=0; i<N; ++i) curr_items[i] = {X[i], i};
    sort(curr_items.begin(), curr_items.end());
    
    vector<pair<int, int>> target_slots(N); 
    for(int i=0; i<N; ++i) target_slots[i] = {Y[i], i};
    sort(target_slots.begin(), target_slots.end());
    
    vector<int> current_targets(N);
    for(int k=0; k<N; ++k) {
        current_targets[curr_items[k].second] = target_slots[k].second;
    }
    
    // Sort items to their target positions using adjacent swaps
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N - 1 - i; ++j) {
            if (current_targets[j] > current_targets[j+1]) {
                apply_op(j, j+1);
                swap(current_targets[j], current_targets[j+1]);
            }
        }
    }
    
    cout << "Yes" << endl;
    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.i << " " << op.j << endl;
    }

    return 0;
}