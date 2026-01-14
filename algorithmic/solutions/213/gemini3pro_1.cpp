#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdlib>
#include <ctime>

using namespace std;

int n;
vector<int> a;
int pos[1005]; // Position lookup
struct Op {
    int l, r, d; // d=0 left, d=1 right
};
vector<Op> ops;

// Apply operation to array 'a' and update 'pos'
void apply_op(int l, int r, int d) {
    ops.push_back({l, r, d});
    if (d == 0) { // Left shift
        int first = a[l];
        for (int i = l; i < r; ++i) {
            a[i] = a[i+1];
            pos[a[i]] = i;
        }
        a[r] = first;
        pos[a[r]] = r;
    } else { // Right shift
        int last = a[r];
        for (int i = r; i > l; --i) {
            a[i] = a[i-1];
            pos[a[i]] = i;
        }
        a[l] = last;
        pos[a[l]] = l;
    }
}

// Simulate operation on a temporary array (for heuristic search)
void sim_op(vector<int>& cur_a, int l, int r, int d) {
    if (d == 0) {
        int first = cur_a[l];
        for (int i = l; i < r; ++i) cur_a[i] = cur_a[i+1];
        cur_a[r] = first;
    } else {
        int last = cur_a[r];
        for (int i = r; i > l; --i) cur_a[i] = cur_a[i-1];
        cur_a[l] = last;
    }
}

// Calculate score for the tail part
long long calc_score(const vector<int>& cur_a, int start_idx) {
    long long sc = 0;
    for (int i = start_idx; i <= n; ++i) {
        int dist = i - cur_a[i];
        sc += dist * dist;
    }
    return sc;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    if (!(cin >> n)) return 0;
    a.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    if (n == 1) {
        cout << "1 0\n";
        return 0;
    }

    // Strategy: x approx sqrt(n). Even x is preferred to ensure tail sortability.
    int x = round(sqrt(n));
    if (x < 2) x = 2;
    if (x % 2 != 0) x++; 
    if (x > n) x = n;
    
    // Sort prefix 1 ... n - x - 1
    int limit = n - x - 1; 
    
    for (int i = 1; i <= limit; ++i) {
        int p = pos[i];
        
        // Phase 1: Long jumps
        // While distance is large enough, jump element to the left
        while (p >= i + x) {
            // R(p - x + 1, p) moves a[p] to p - x + 1 (left by x-1)
            apply_op(p - x + 1, p, 1);
            p = pos[i]; 
        }

        // Phase 2: Fine tuning
        // Element is now in [i, i+x-1]. Use rotations of this window to place it at i.
        while (pos[i] != i) {
             // L(i, i+x-1) moves element at i to end, effectively shifting target left
             apply_op(i, i + x - 1, 0);
        }
    }

    // Sort tail: range [limit + 1, n]
    // Tail size is x + 1. We have windows of size x.
    int tail_start = limit + 1;
    if (tail_start < 1) tail_start = 1;
    
    // Identify valid windows in the tail
    vector<pair<int, int>> valid_windows;
    for (int s = tail_start; s <= n - x + 1; ++s) {
        valid_windows.push_back({s, s + x - 1});
    }
    
    // Hill climbing / Randomized search to sort the tail
    int max_iter = 50000;
    int iter = 0;
    
    while (iter < max_iter) {
        long long current_score = calc_score(a, tail_start);
        if (current_score == 0) break;
        
        long long best_score = -1;
        int best_w = -1;
        int best_d = -1;
        
        // Try all possible moves
        for (int i = 0; i < valid_windows.size(); ++i) {
            int l = valid_windows[i].first;
            int r = valid_windows[i].second;
            for (int d = 0; d < 2; ++d) {
                vector<int> next_a = a;
                sim_op(next_a, l, r, d);
                long long sc = calc_score(next_a, tail_start);
                if (best_score == -1 || sc < best_score) {
                    best_score = sc;
                    best_w = i;
                    best_d = d;
                }
            }
        }
        
        // Apply best move if it improves, otherwise random move to escape local optima
        if (best_score < current_score) {
            apply_op(valid_windows[best_w].first, valid_windows[best_w].second, best_d);
        } else {
            int w = rand() % valid_windows.size();
            int d = rand() % 2;
            apply_op(valid_windows[w].first, valid_windows[w].second, d);
        }
        iter++;
    }

    cout << x << " " << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.l << " " << op.l + x - 1 << " " << op.d << "\n";
    }

    return 0;
}