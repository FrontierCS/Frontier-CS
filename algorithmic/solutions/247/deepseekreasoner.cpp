#include <bits/stdc++.h>
using namespace std;

int N;
vector<int> A, B, S;

// Compute the change in |S[i]|+|S[j]| if operation (i,j) is applied.
// Returns delta, T, new_Si, new_Sj.
tuple<int, int, int, int> compute_delta(int i, int j) {
    int T = (B[j] - B[i] - 1) + (S[i] - S[j]);
    int new_Si = S[i] - T;
    int new_Sj = S[j] + T;
    int old_abs = abs(S[i]) + abs(S[j]);
    int new_abs = abs(new_Si) + abs(new_Sj);
    int delta = new_abs - old_abs;
    return {delta, T, new_Si, new_Sj};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> N;
    A.resize(N);
    B.resize(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    for (int i = 0; i < N; i++) cin >> B[i];
    
    // Compute initial difference S = B - A
    S.resize(N);
    int sumS = 0;
    for (int i = 0; i < N; i++) {
        S[i] = B[i] - A[i];
        sumS += S[i];
    }
    if (sumS != 0) {
        cout << "No\n";
        return 0;
    }
    
    vector<pair<int, int>> ops;
    const int MAX_OPS = 100000; // safety limit
    int steps = 0;
    
    // To avoid cycling, we keep a set of visited S states (hashed).
    // Since N <= 100 and values are small, we use a vector as key.
    auto hash_vector = [](const vector<int>& v) {
        size_t seed = v.size();
        for (int x : v) {
            seed ^= x + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        }
        return seed;
    };
    unordered_set<size_t> visited;
    
    while (steps < MAX_OPS) {
        // Check if S is all zero
        bool done = true;
        for (int x : S) if (x != 0) { done = false; break; }
        if (done) break;
        
        size_t h = hash_vector(S);
        if (visited.count(h)) {
            // Cycle detected; cannot proceed.
            cout << "No\n";
            return 0;
        }
        visited.insert(h);
        
        // Look for an operation that immediately reduces L1 norm.
        int best_delta = 0;
        int best_i = -1, best_j = -1, best_T = 0;
        vector<tuple<int, int, int, int, int>> candidates; // (delta, i, j, T, zero_flag)
        for (int i = 0; i < N; i++) {
            for (int j = i+1; j < N; j++) {
                auto [delta, T, new_Si, new_Sj] = compute_delta(i, j);
                if (delta < 0) {
                    bool zero = (new_Si == 0 || new_Sj == 0);
                    candidates.emplace_back(delta, i, j, T, zero);
                }
            }
        }
        
        if (!candidates.empty()) {
            // Prefer candidates that zero out an S component.
            sort(candidates.begin(), candidates.end(), [](const auto& a, const auto& b) {
                if (get<4>(a) != get<4>(b)) return get<4>(a) > get<4>(b); // zero first
                return get<0>(a) < get<0>(b); // more negative delta first
            });
            auto [delta, i, j, T, _] = candidates[0];
            // Apply operation
            S[i] -= T;
            S[j] += T;
            ops.emplace_back(i+1, j+1);
            steps++;
            continue;
        }
        
        // No immediate reduction: try lookahead.
        bool found = false;
        // We'll consider moves that do not increase L1 by more than 2 (heuristic).
        for (int i = 0; i < N && !found; i++) {
            for (int j = i+1; j < N && !found; j++) {
                auto [delta0, T0, new_Si, new_Sj] = compute_delta(i, j);
                if (delta0 > 2) continue; // avoid large increases
                // Simulate this move
                vector<int> tempS = S;
                tempS[i] = new_Si;
                tempS[j] = new_Sj;
                // Check if from tempS there is any reducing move.
                for (int k = 0; k < N; k++) {
                    for (int l = k+1; l < N; l++) {
                        int T2 = (B[l] - B[k] - 1) + (tempS[k] - tempS[l]);
                        int new_Sk = tempS[k] - T2;
                        int new_Sl = tempS[l] + T2;
                        int old_abs = abs(tempS[k]) + abs(tempS[l]);
                        int new_abs = abs(new_Sk) + abs(new_Sl);
                        if (new_abs < old_abs) {
                            found = true;
                            break;
                        }
                    }
                    if (found) break;
                }
                if (found) {
                    // Apply the move (i,j)
                    S[i] = new_Si;
                    S[j] = new_Sj;
                    ops.emplace_back(i+1, j+1);
                    steps++;
                    break;
                }
            }
        }
        
        if (!found) {
            // No good move found; assume impossible.
            cout << "No\n";
            return 0;
        }
    }
    
    if (steps >= MAX_OPS) {
        cout << "No\n";
        return 0;
    }
    
    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto [i, j] : ops) {
        cout << i << " " << j << "\n";
    }
    return 0;
}