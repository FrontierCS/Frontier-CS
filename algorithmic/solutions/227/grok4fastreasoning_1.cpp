#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    vector<int> p(n);
    for (int &x : p) cin >> x;
    
    vector<int> a, b, c, d;
    int last_a = 0, last_b = n + 1;
    int last_c = 0, last_d = n + 1;
    
    for (int v : p) {
        // Find best inc (0: a, 1: c)
        int best_inc_j = -1;
        int max_l_inc = INT_MIN;
        if (last_a < v) {
            if (last_a > max_l_inc) {
                max_l_inc = last_a;
                best_inc_j = 0;
            }
        }
        if (last_c < v) {
            if (last_c > max_l_inc) {
                max_l_inc = last_c;
                best_inc_j = 1;
            }
        }
        long long dist_inc = (best_inc_j == -1 ? LLONG_MAX / 2 : (long long)v - max_l_inc);
        
        // Find best dec (0: b, 1: d)
        int best_dec_j = -1;
        int min_l_dec = INT_MAX;
        if (last_b > v) {
            if (last_b < min_l_dec) {
                min_l_dec = last_b;
                best_dec_j = 0;
            }
        }
        if (last_d > v) {
            if (last_d < min_l_dec) {
                min_l_dec = last_d;
                best_dec_j = 1;
            }
        }
        long long dist_dec = (best_dec_j == -1 ? LLONG_MAX / 2 : (long long)min_l_dec - v);
        
        // Decide
        bool choose_inc = false;
        if (dist_inc == LLONG_MAX / 2 && dist_dec == LLONG_MAX / 2) {
            // Should not happen
            assert(false);
        } else if (dist_inc == LLONG_MAX / 2) {
            choose_inc = false;
        } else if (dist_dec == LLONG_MAX / 2) {
            choose_inc = true;
        } else {
            if (dist_inc < dist_dec) {
                choose_inc = true;
            } else if (dist_dec < dist_inc) {
                choose_inc = false;
            } else {
                // Tie, prefer inc
                choose_inc = true;
            }
        }
        
        // Append
        if (choose_inc) {
            if (best_inc_j == 0) {
                a.push_back(v);
                last_a = v;
            } else {
                c.push_back(v);
                last_c = v;
            }
        } else {
            if (best_dec_j == 0) {
                b.push_back(v);
                last_b = v;
            } else {
                d.push_back(v);
                last_d = v;
            }
        }
    }
    
    // Output
    cout << a.size() << " " << b.size() << " " << c.size() << " " << d.size() << "\n";
    for (size_t i = 0; i < a.size(); ++i) {
        cout << a[i];
        if (i + 1 < a.size()) cout << " ";
    }
    cout << "\n";
    for (size_t i = 0; i < b.size(); ++i) {
        cout << b[i];
        if (i + 1 < b.size()) cout << " ";
    }
    cout << "\n";
    for (size_t i = 0; i < c.size(); ++i) {
        cout << c[i];
        if (i + 1 < c.size()) cout << " ";
    }
    cout << "\n";
    for (size_t i = 0; i < d.size(); ++i) {
        cout << d[i];
        if (i + 1 < d.size()) cout << " ";
    }
    cout << "\n";
    
    return 0;
}