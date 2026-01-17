#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <queue>

using namespace std;

// Operation struct
struct Op {
    int l, r, d; // d=0 left, d=1 right
};

int N;
vector<int> A;
vector<Op> ops;
int X;

// Apply operation to array A
void apply_op(int l, int r, int d, vector<int>& arr) {
    // 1-based l, r
    // Segment length is X
    // d=0: left shift: a[l] moves to r, a[l+1...r] moves to l...r-1
    // d=1: right shift: a[r] moves to l, a[l...r-1] moves to l+1...r
    if (d == 0) {
        int first = arr[l-1];
        for (int i = l - 1; i < r - 1; ++i) {
            arr[i] = arr[i+1];
        }
        arr[r-1] = first;
    } else {
        int last = arr[r-1];
        for (int i = r - 1; i > l - 1; --i) {
            arr[i] = arr[i-1];
        }
        arr[l-1] = last;
    }
}

void record_op(int l, int r, int d) {
    ops.push_back({l, r, d});
    apply_op(l, r, d, A);
}

int get_pos(int val) {
    for(int i=0; i<N; ++i) if(A[i] == val) return i + 1;
    return -1;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    A.resize(N);
    for(int i=0; i<N; ++i) cin >> A[i];

    // Strategy decision based on N
    // For small N, X=2 allows full bubble sort within limits.
    // For large N, X=40 balances jump efficiency and suffix sorting cost.
    if (N <= 46) {
        X = 2;
    } else {
        X = 40; 
    }
    
    // Main phase: Place elements 1 to N-X
    for (int i = 1; i <= N - X; ++i) {
        int target_val = i;
        int pos = get_pos(target_val); // 1-based
        
        // Phase 1: Jumps to bring element closer to position i
        while (pos >= i + X) {
            // Right shift on [pos-X+1, pos] moves element at pos to pos-X+1
            // Distance reduced by X-1
            record_op(pos - X + 1, pos, 1);
            pos = pos - X + 1;
        }
        
        // Phase 2: Local Adjustment inside window [i, i+X-1]
        // Target is now at pos, with i <= pos < i+X
        // We use window [i, i+X-1] to move it to i.
        
        int d_left = pos - i;       // Cost using left shifts (pos -> pos-1)
        int d_right = i + X - pos;  // Cost using right shifts (pos -> pos+1 -> ... -> wrap)
        
        if (d_left <= d_right) {
            for(int k=0; k<d_left; ++k) record_op(i, i+X-1, 0);
        } else {
            for(int k=0; k<d_right; ++k) record_op(i, i+X-1, 1);
        }
    }
    
    // Suffix phase: Sort the last X+1 elements
    // Range indices: N-X ... N (1-based)
    // For X > 2, we use A* search to sort the remaining block
    if (X > 2) {
        int start_idx = N - X - 1; // 0-based start of suffix block
        vector<int> suffix;
        for(int k=0; k<=X; ++k) suffix.push_back(A[start_idx+k]);
        
        vector<int> target = suffix;
        sort(target.begin(), target.end());
        
        // Heuristic function for A*
        auto calc_h = [&](const vector<int>& v) {
            int h = 0;
            for(int i=0; i<=X; ++i) {
                int val = v[i];
                int target_idx = val - (N-X); 
                h += abs(i - target_idx);
            }
            return h;
        };
        
        // A* Search
        priority_queue<pair<int, vector<int>>, vector<pair<int, vector<int>>>, greater<pair<int, vector<int>>>> pq;
        map<vector<int>, int> g_score;
        map<vector<int>, int> last_move;
        map<vector<int>, vector<int>> parent;
        
        g_score[suffix] = 0;
        pq.push({calc_h(suffix), suffix});
        
        bool solved = false;
        vector<int> final_state;
        int iter = 0;
        
        while(!pq.empty()) {
            auto top = pq.top();
            pq.pop();
            int f = top.first;
            vector<int> u = top.second;
            
            if (f > g_score[u] + calc_h(u) * 2) continue; // Optimization
            
            if (u == target) {
                solved = true;
                final_state = u;
                break;
            }
            
            if (iter++ > 200000) break; // Time limit safety
            
            int g = g_score[u];
            if (g > 600) continue; // Ops limit safety
            
            // Try 4 moves: L-Left, L-Right, R-Left, R-Right
            // L operates on first X elements of suffix block
            // R operates on last X elements of suffix block
            for(int t=0; t<4; ++t) {
                vector<int> v = u;
                int l, r, d;
                // Local indices 0..X
                if (t == 0) { l=0; r=X-1; d=0; }
                else if (t == 1) { l=0; r=X-1; d=1; }
                else if (t == 2) { l=1; r=X; d=0; }
                else { l=1; r=X; d=1; }
                
                if (d == 0) {
                    int first = v[l];
                    for (int k = l; k < r; ++k) v[k] = v[k+1];
                    v[r] = first;
                } else {
                    int last = v[r];
                    for (int k = r; k > l; --k) v[k] = v[k-1];
                    v[l] = last;
                }
                
                int new_g = g + 1;
                if (g_score.find(v) == g_score.end() || new_g < g_score[v]) {
                    g_score[v] = new_g;
                    last_move[v] = t;
                    parent[v] = u;
                    int h = calc_h(v);
                    pq.push({new_g + h + h/2, v}); 
                }
            }
        }
        
        if (solved) {
            vector<int> path;
            vector<int> curr = final_state;
            while(curr != suffix) {
                path.push_back(last_move[curr]);
                curr = parent[curr];
            }
            reverse(path.begin(), path.end());
            for(int t : path) {
                int l, r, d;
                // Map back to global 1-based indices
                if (t == 0) { l = start_idx + 1; r = start_idx + X; d = 0; }
                else if (t == 1) { l = start_idx + 1; r = start_idx + X; d = 1; }
                else if (t == 2) { l = start_idx + 2; r = start_idx + X + 1; d = 0; }
                else { l = start_idx + 2; r = start_idx + X + 1; d = 1; }
                record_op(l, r, d);
            }
        }
    } else {
        // X=2 case: Handle potential last swap
        if (A[N-2] > A[N-1]) {
            record_op(N-1, N, 1);
        }
    }

    cout << X << " " << ops.size() << "\n";
    for(const auto& op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }

    return 0;
}