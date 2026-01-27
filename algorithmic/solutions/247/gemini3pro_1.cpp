#include <iostream>
#include <vector>
#include <numeric>
#include <queue>
#include <algorithm>
#include <tuple>

using namespace std;

struct State {
    int idx;
    int val;
};

struct Transition {
    int p_idx;
    int p_val;
};

const int OFFSET = 250;
const int MAX_VAL_IDX = 600;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    if (!(cin >> N)) return 0;

    vector<int> A(N + 1);
    long long sumA = 0;
    for (int i = 1; i <= N; ++i) {
        cin >> A[i];
        sumA += A[i];
    }

    vector<int> B(N + 1);
    long long sumB = 0;
    for (int i = 1; i <= N; ++i) {
        cin >> B[i];
        sumB += B[i];
    }

    if (sumA != sumB) {
        cout << "No" << endl;
        return 0;
    }

    vector<pair<int, int>> operations;

    for (int i = 1; i <= N; ++i) {
        if (A[i] == B[i]) continue;

        // BFS to find a sequence of swaps to bring a value to position i that matches B[i]
        // We search backwards from the target state (i, B[i]) to a source state (j, A[j])
        // The BFS state tracks the position and value of the element we want to move to i.
        
        vector<vector<int>> dist(N + 1, vector<int>(MAX_VAL_IDX, -1));
        vector<vector<Transition>> parent(N + 1, vector<Transition>(MAX_VAL_IDX));
        
        queue<State> q;
        int target_val = B[i];
        
        if (target_val + OFFSET < 0 || target_val + OFFSET >= MAX_VAL_IDX) {
            cout << "No" << endl;
            return 0;
        }

        dist[i][target_val + OFFSET] = 0;
        q.push({i, target_val});
        
        State found_source = {-1, -1};

        while (!q.empty()) {
            State curr = q.front();
            q.pop();

            int u = curr.idx;
            int v_val = curr.val;

            // Check if A[u] matches the required value.
            // u must be >= i because positions 1..i-1 are already fixed.
            if (u >= i && A[u] == v_val) {
                found_source = curr;
                break;
            }

            // Try reverse transitions
            // In the forward process, if we swap(u, k) with u < k:
            //   Item at u moves to k and value increases by 1.
            //   Item at k moves to u and value decreases by 1.
            // Here 'curr' represents the position of our item of interest.
            // We want to find where it came from.
            
            // Case 1: We came from k (k > u). The item moved k -> u (Left).
            // A left move decreases value by 1. So prev_val - 1 = v_val => prev_val = v_val + 1.
            // This corresponds to a swap(u, k) where u < k.
            
            // Case 2: We came from k (k < u). The item moved k -> u (Right).
            // A right move increases value by 1. So prev_val + 1 = v_val => prev_val = v_val - 1.
            // This corresponds to a swap(k, u) where k < u.
            
            // We only consider swaps with indices >= i.
            
            for (int k = i; k <= N; ++k) {
                if (u == k) continue;
                
                int prev_val;
                if (u < k) { 
                    // To reach u from k (k > u), it's a left move.
                    prev_val = v_val + 1;
                } else {
                    // To reach u from k (k < u), it's a right move.
                    prev_val = v_val - 1;
                }
                
                if (prev_val + OFFSET >= 0 && prev_val + OFFSET < MAX_VAL_IDX) {
                    if (dist[k][prev_val + OFFSET] == -1) {
                        dist[k][prev_val + OFFSET] = dist[u][v_val + OFFSET] + 1;
                        parent[k][prev_val + OFFSET] = {u, v_val}; 
                        q.push({k, prev_val});
                    }
                }
            }
        }

        if (found_source.idx == -1) {
            cout << "No" << endl;
            return 0;
        }

        // Reconstruct path and apply operations
        State curr = found_source;
        while (curr.idx != i || curr.val != target_val) {
            Transition t = parent[curr.idx][curr.val + OFFSET];
            int next_idx = t.p_idx;
            int next_val = t.p_val;
            
            int p1 = curr.idx;
            int p2 = next_idx;
            if (p1 > p2) swap(p1, p2);
            
            operations.push_back({p1, p2});
            
            // Apply swap to A
            int val1 = A[p1];
            int val2 = A[p2];
            A[p1] = val2 - 1;
            A[p2] = val1 + 1;
            
            curr = {next_idx, next_val};
        }
    }

    cout << "Yes" << endl;
    cout << operations.size() << endl;
    for (auto p : operations) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}