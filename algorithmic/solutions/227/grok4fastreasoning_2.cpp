#include <bits/stdc++.h>
using namespace std;

int lis_len(const vector<int>& v) {
    if (v.empty()) return 0;
    vector<int> tails;
    for (int x : v) {
        auto it = lower_bound(tails.begin(), tails.end(), x);
        if (it == tails.end()) {
            tails.push_back(x);
        } else {
            *it = x;
        }
    }
    return tails.size();
}

int lds_len(const vector<int>& v) {
    if (v.empty()) return 0;
    vector<int> neg;
    neg.reserve(v.size());
    for (int x : v) {
        neg.push_back(-x);
    }
    return lis_len(neg);
}

int compute_sum(const vector<vector<int>>& parts) {
    int s = 0;
    s += lis_len(parts[0]);
    s += lds_len(parts[1]);
    s += lis_len(parts[2]);
    s += lds_len(parts[3]);
    return s;
}

vector<vector<int>> get_parts(const vector<int>& p, bool prefer_inc, int n) {
    vector<vector<int>> vec(4);
    vector<int> lasts(4);
    lasts[0] = 0; // A inc
    lasts[1] = n + 1; // B dec
    lasts[2] = 0; // C inc
    lasts[3] = n + 1; // D dec
    for (int x : p) {
        bool assigned = false;
        if (prefer_inc) {
            // Try inc: 0 and 2
            int chosen = -1;
            int max_t = INT_MIN;
            for (int s : {0, 2}) {
                if (lasts[s] < x && lasts[s] > max_t) {
                    max_t = lasts[s];
                    chosen = s;
                }
            }
            if (chosen != -1) {
                vec[chosen].push_back(x);
                lasts[chosen] = x;
                assigned = true;
            }
            if (!assigned) {
                // Try dec: 1 and 3
                int ch = -1;
                int min_t = INT_MAX;
                for (int s : {1, 3}) {
                    if (lasts[s] > x && lasts[s] < min_t) {
                        min_t = lasts[s];
                        ch = s;
                    }
                }
                if (ch != -1) {
                    vec[ch].push_back(x);
                    lasts[ch] = x;
                    assigned = true;
                }
            }
            if (!assigned) {
                // Force to 1 (B)
                vec[1].push_back(x);
                lasts[1] = x;
            }
        } else {
            // Prefer dec: first try dec 1 and 3
            int chosen = -1;
            int min_t = INT_MAX;
            for (int s : {1, 3}) {
                if (lasts[s] > x && lasts[s] < min_t) {
                    min_t = lasts[s];
                    chosen = s;
                }
            }
            if (chosen != -1) {
                vec[chosen].push_back(x);
                lasts[chosen] = x;
                assigned = true;
            }
            if (!assigned) {
                // Try inc: 0 and 2
                int ch = -1;
                int max_t = INT_MIN;
                for (int s : {0, 2}) {
                    if (lasts[s] < x && lasts[s] > max_t) {
                        max_t = lasts[s];
                        ch = s;
                    }
                }
                if (ch != -1) {
                    vec[ch].push_back(x);
                    lasts[ch] = x;
                    assigned = true;
                }
            }
            if (!assigned) {
                // Force to 0 (A)
                vec[0].push_back(x);
                lasts[0] = x;
            }
        }
    }
    return vec;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<int> p(n);
    for (int& x : p) cin >> x;
    auto parts1 = get_parts(p, true, n);
    int sum1 = compute_sum(parts1);
    auto parts2 = get_parts(p, false, n);
    int sum2 = compute_sum(parts2);
    vector<vector<int>> best;
    if (sum1 >= sum2) {
        best = parts1;
    } else {
        best = parts2;
    }
    cout << best[0].size() << " " << best[1].size() << " " << best[2].size() << " " << best[3].size() << "\n";
    for (const auto& v : best) {
        for (int x : v) {
            cout << x << " ";
        }
        cout << "\n";
    }
    return 0;
}