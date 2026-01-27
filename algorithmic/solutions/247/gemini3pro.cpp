#include <iostream>
#include <vector>
#include <numeric>
#include <queue>
#include <algorithm>

using namespace std;

// Maximum value offset and array size
// Values are in range [1, 100] initially.
// Operations can decrease/increase values.
// Max path length is around N. So values won't drift by more than N.
// Range [-200, 300] is sufficient.
const int OFFSET = 350;
const int MAX_VAL = 800; 

struct State {
    int u;
    int val;
};

int N;
vector<int> A, B;
vector<pair<int, int>> ans;

// Visited array using token to avoid memset overhead
int visited[105][MAX_VAL];
int visited_token = 0;
pair<int, int> parent[105][MAX_VAL];

// Perform operation on global array A and record it
void apply_op(int u, int v) {
    if (u == v) return;
    int x = min(u, v);
    int y = max(u, v);
    ans.push_back({x, y});
    int ax = A[x];
    int ay = A[y];
    A[x] = ay - 1;
    A[y] = ax + 1;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    A.resize(N + 1);
    long long sumA = 0;
    for (int i = 1; i <= N; ++i) {
        cin >> A[i];
        sumA += A[i];
    }

    B.resize(N + 1);
    long long sumB = 0;
    for (int i = 1; i <= N; ++i) {
        cin >> B[i];
        sumB += B[i];
    }

    // A necessary condition is equal sums
    if (sumA != sumB) {
        cout << "No" << endl;
        return 0;
    }

    // Greedy strategy: Fix elements from 1 to N one by one.
    // For each position i, we want to bring an element with value B[i] to position i
    // using minimal operations involving only indices [i, N].
    for (int i = 1; i <= N; ++i) {
        if (A[i] == B[i]) continue;

        visited_token++;
        queue<State> Q;

        // We run a BFS backwards from the target state (pos=i, val=B[i])
        // We want to find a reachable state (pos=k, val=A[k]) where k >= i.
        // This corresponds to moving an element currently at k with value A[k] to i,
        // such that its value becomes B[i].
        int start_val = B[i];
        
        if (start_val + OFFSET >= 0 && start_val + OFFSET < MAX_VAL) {
            visited[i][start_val + OFFSET] = visited_token;
            Q.push({i, start_val});
        }

        int found_k = -1;
        int found_val = -1;

        while (!Q.empty()) {
            State curr = Q.front();
            Q.pop();

            int u = curr.u;
            int val = curr.val;

            // Check if current position u holds an element with the required value
            if (A[u] == val) {
                found_k = u;
                found_val = val;
                break;
            }

            // Backward transitions:
            // We came to u from some v.
            // Forward move: v -> u.
            // If v < u: Element moved right. Value increased by 1. val = prev_val + 1 => prev_val = val - 1.
            // If v > u: Element moved left. Value decreased by 1. val = prev_val - 1 => prev_val = val + 1.
            
            for (int v = i; v <= N; ++v) {
                if (u == v) continue;

                int prev_val;
                if (v < u) {
                    prev_val = val - 1;
                } else {
                    prev_val = val + 1;
                }

                if (prev_val + OFFSET >= 0 && prev_val + OFFSET < MAX_VAL) {
                    if (visited[v][prev_val + OFFSET] != visited_token) {
                        visited[v][prev_val + OFFSET] = visited_token;
                        parent[v][prev_val + OFFSET] = {u, val};
                        Q.push({v, prev_val});
                    }
                }
            }
        }

        if (found_k == -1) {
            // Cannot satisfy A[i] == B[i]
            cout << "No" << endl;
            return 0;
        }

        // Reconstruct path and apply operations
        // The parent pointers lead from source (found_k) towards target (i)
        // This matches the order of operations we need to perform.
        int curr_u = found_k;
        int curr_val = found_val;

        while (curr_u != i || curr_val != B[i]) {
            pair<int, int> nxt = parent[curr_u][curr_val + OFFSET];
            int next_u = nxt.first;
            int next_val = nxt.second;

            apply_op(curr_u, next_u);

            curr_u = next_u;
            curr_val = next_val;
        }
    }

    cout << "Yes" << endl;
    cout << ans.size() << endl;
    for (const auto &p : ans) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}