#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>

using namespace std;

int n;
vector<int> a;
struct Op {
    int l, r;
};
vector<Op> ops;

void perform_reverse(int l, int r) {
    reverse(a.begin() + l - 1, a.begin() + r);
}

void record_op(int l, int r) {
    ops.push_back({l, r});
}

// Calculate score for the suffix starting at start_idx
// Score is weighted sum of distance to correct position and inversions
int calc_score_suffix(int start_idx) {
    int dist_score = 0;
    int inv_score = 0;
    // We only care about the sorting of the suffix region
    // The values in this region should be sorted relative to each other
    // and ideally equal to their index (since we fixed prefix).
    
    for (int i = start_idx; i <= n; ++i) {
        dist_score += abs(a[i-1] - i);
    }
    
    // Check inversions only within the suffix
    for (int i = start_idx; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            if (a[i-1] > a[j-1]) inv_score++;
        }
    }
    return dist_score + inv_score * 5; // Weight inversions more heavily
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    a.resize(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    int x;
    if (n <= 60) x = 1; // Use bubble sort-ish for small N
    else x = 21; // Odd number, lengths 20 and 22 for speed

    cout << x << "\n";

    int L1 = x - 1;
    int L2 = x + 1;
    vector<int> lens;
    if (L1 > 0) lens.push_back(L1);
    lens.push_back(L2);

    // We sort greedily until the suffix is small
    int limit = n;
    if (x > 1) limit = n - 40; 
    if (limit < 1) limit = 1;

    for (int i = 1; i <= limit; ++i) {
        // Find current position of value i
        int pos = -1;
        for (int j = 0; j < n; ++j) {
            if (a[j] == i) {
                pos = j + 1;
                break;
            }
        }

        // Move element i to position i
        while (pos > i) {
            // Try to find a move that lands exactly on i
            bool landed = false;
            for (int len : lens) {
                // target: l + r - pos = i  => 2l + len - 1 - pos = i
                // 2l = i + pos - len + 1
                long long val = (long long)i + pos - len + 1;
                if (val % 2 == 0) {
                    int try_l = val / 2;
                    int try_r = try_l + len - 1;
                    // Check bounds: l >= i to preserve sorted prefix
                    // and l <= pos <= r to include the element
                    if (try_l >= i && try_r <= n && try_l <= pos && pos <= try_r) {
                        perform_reverse(try_l, try_r);
                        record_op(try_l, try_r);
                        pos = i;
                        landed = true;
                        break;
                    }
                }
            }
            if (landed) break;

            // If exact landing not possible, move greedily to the left
            int best_new_pos = 1e9;
            int best_l = -1, best_r = -1;

            for (int len : lens) {
                // To minimize new_pos = l + r - pos = 2l + len - 1 - pos
                // We need to minimize l.
                // Constraint: l >= i, r <= n, l <= pos <= r.
                
                // Case 1: pos is within [i, i + len - 1]
                // We can pick l=i (minimal l)
                if (pos >= i && pos <= i + len - 1) {
                    int l = i;
                    int r = i + len - 1;
                    if (r <= n) {
                        int np = l + r - pos;
                        if (np < best_new_pos) {
                            best_new_pos = np;
                            best_l = l;
                            best_r = r;
                        }
                    }
                }
                
                // Case 2: pos > i + len - 1
                // Minimal valid l is such that r >= pos => l + len - 1 >= pos => l >= pos - len + 1
                int l = pos - len + 1;
                int r = l + len - 1; // r = pos
                // Check bounds
                if (l >= i && r <= n) {
                    int np = l + r - pos; // = pos - len + 1 + pos - pos = pos - len + 1
                    if (np < best_new_pos) {
                        best_new_pos = np;
                        best_l = l;
                        best_r = r;
                    }
                }
            }

            if (best_l != -1) {
                perform_reverse(best_l, best_r);
                record_op(best_l, best_r);
                pos = best_new_pos;
            } else {
                // Should not happen if x is chosen reasonably wrt n
                break;
            }
        }
    }

    // Phase 2: Sort the remaining suffix using local search
    // Region to sort: [limit + 1, n]
    // However, if we just use operations strictly inside this region, we might get stuck?
    // With x=21, region size 40, lengths 20,22, we have enough freedom.
    if (x > 1 && limit < n) {
        int region_start = limit + 1;
        int current_score = calc_score_suffix(region_start);
        
        mt19937 rng(12345);
        int iter = 0;
        int max_ops = 200 * n; 
        
        while (current_score > 0 && ops.size() < max_ops) {
            bool improved = false;
            
            // Try a few random moves
            for (int t = 0; t < 15; ++t) {
                int len = lens[rng() % lens.size()];
                int max_l = n - len + 1;
                if (max_l < region_start) continue;
                
                int l = region_start + rng() % (max_l - region_start + 1);
                int r = l + len - 1;
                
                perform_reverse(l, r);
                int new_score = calc_score_suffix(region_start);
                
                if (new_score < current_score) {
                    record_op(l, r);
                    current_score = new_score;
                    improved = true;
                    break; 
                } else {
                    // Revert
                    perform_reverse(l, r);
                }
            }
            
            if (!improved) {
                // Accept a random move to escape local optima
                int len = lens[rng() % lens.size()];
                int max_l = n - len + 1;
                if (max_l >= region_start) {
                    int l = region_start + rng() % (max_l - region_start + 1);
                    int r = l + len - 1;
                    perform_reverse(l, r);
                    record_op(l, r);
                    current_score = calc_score_suffix(region_start);
                }
            }
            iter++;
            if (iter > 50000) break; // Safety break
        }
    }

    cout << ops.size() << "\n";
    for (const auto& p : ops) {
        cout << p.l << " " << p.r << "\n";
    }

    return 0;
}