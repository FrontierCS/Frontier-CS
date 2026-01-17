#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <deque>

using namespace std;

// Global variables
int n;
vector<int> a;
struct Op {
    int l, r, d; // d=0 left, d=1 right
};
vector<Op> ops;

// Function to apply operation and record it
void apply_op(int l, int r, int d) {
    // 1-based index in input, convert to 0-based for vector access
    if (d == 0) { // Left shift
        int first = a[l-1];
        for (int i = l-1; i < r-1; ++i) {
            a[i] = a[i+1];
        }
        a[r-1] = first;
    } else { // Right shift
        int last = a[r-1];
        for (int i = r-1; i > l-1; --i) {
            a[i] = a[i-1];
        }
        a[l-1] = last;
    }
    ops.push_back({l, r, d});
}

// Find current position of value val (1-based)
int get_pos(int val) {
    for (int i = 0; i < n; ++i) {
        if (a[i] == val) return i + 1;
    }
    return -1;
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    a.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    // Heuristic choice for x
    // x = 24 works well for n=1000 to keep within 23n operations
    // For smaller n, we adjust x
    int x = 24;
    if (n <= 30) x = n / 2; 
    if (x < 2) x = 2; 

    // Phase 1: Sort 1 to n - x - 1 using greedy approach
    // We stop at n - x - 1 to ensure we have at least 2 overlapping windows for the suffix sort
    int limit = n - x - 1;
    if (limit < 0) limit = 0;

    for (int val = 1; val <= limit; ++val) {
        int pos = get_pos(val);
        // We want to move val from pos to val
        
        // Step 1: Long jumps (Right Shift)
        // We can move the element to the left by x-1 steps
        while (pos - (x - 1) >= val) {
            apply_op(pos - x + 1, pos, 1); 
            pos -= (x - 1);
        }

        // Step 2: Fine tuning (Left Shift on [val, val+x-1])
        // This moves the element at pos one step to the left
        // Valid because pos > val and range is valid
        while (pos > val) {
            apply_op(val, val + x - 1, 0); 
            pos = get_pos(val); // Re-evaluate position
        }
    }

    // Phase 2: Sort the remaining suffix from limit + 1 to n
    // We use BFS to find the shortest sequence of operations to place each element
    for (int val = limit + 1; val <= n - 1; ++val) {
        while (true) {
            int pos = get_pos(val);
            if (pos == val) break;
            
            // Generate valid operations
            // Operations must be within [val, n] to not disturb the sorted prefix 1..val-1
            vector<pair<int, int>> valid_ops; 
            for (int L = val; L <= n - x + 1; ++L) {
                valid_ops.push_back({L, 0});
                valid_ops.push_back({L, 1});
            }
            
            // BFS to move 'val' from 'pos' to 'val'
            // We only care about the position of 'val'
            vector<int> dist(n + 1, -1);
            vector<int> from(n + 1, -1);
            vector<int> op_id(n + 1, -1);
            
            deque<int> q;
            q.push_back(pos);
            dist[pos] = 0;
            
            bool found = false;
            while (!q.empty()) {
                int u = q.front();
                q.pop_front();
                
                if (u == val) {
                    found = true;
                    break;
                }
                
                for (int k = 0; k < valid_ops.size(); ++k) {
                    int L = valid_ops[k].first;
                    int R = L + x - 1;
                    int d = valid_ops[k].second;
                    
                    int v = u;
                    if (u >= L && u <= R) {
                        if (d == 0) { // Left
                            if (u == L) v = R;
                            else v = u - 1;
                        } else { // Right
                            if (u == R) v = L;
                            else v = u + 1;
                        }
                    }
                    
                    if (dist[v] == -1) {
                        dist[v] = dist[u] + 1;
                        from[v] = u;
                        op_id[v] = k;
                        q.push_back(v);
                    }
                }
            }
            
            if (found) {
                // Execute only the first step of the path
                vector<int> path;
                int curr = val;
                while (curr != pos) {
                    path.push_back(op_id[curr]);
                    curr = from[curr];
                }
                int k = path.back();
                apply_op(valid_ops[k].first, valid_ops[k].first + x - 1, valid_ops[k].second);
            } else {
                // If stuck (should not happen with sufficient x), try a random valid move
                if (!valid_ops.empty()) {
                     apply_op(valid_ops[0].first, valid_ops[0].first + x - 1, valid_ops[0].second);
                } else {
                    break; 
                }
            }
        }
    }

    cout << x << " " << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }

    return 0;
}