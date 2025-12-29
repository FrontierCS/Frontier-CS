#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);
    if (tokens.empty()) return 0;

    auto solve_single = [](const vector<long long>& arr) -> int {
        int n = (int)arr.size();
        int pos_n = -1, pos_max = 0;
        long long mx = LLONG_MIN;
        for (int i = 0; i < n; ++i) {
            if (arr[i] == n) pos_n = i;
            if (arr[i] > mx) {
                mx = arr[i];
                pos_max = i;
            }
        }
        if (pos_n != -1) return pos_n + 1;
        return pos_max + 1;
    };

    size_t idx = 0;
    bool ok_multi = false;
    vector<vector<long long>> tests;

    if (tokens.size() >= 2) {
        long long T = tokens[idx++];
        vector<vector<long long>> tmp;
        bool ok = true;
        for (long long t = 0; t < T; ++t) {
            if (idx >= tokens.size()) { ok = false; break; }
            long long n = tokens[idx++];
            if (n < 0 || idx + (size_t)n > tokens.size()) { ok = false; break; }
            vector<long long> arr;
            arr.reserve(n);
            for (long long i = 0; i < n; ++i) arr.push_back(tokens[idx++]);
            tmp.push_back(move(arr));
        }
        if (ok && idx == tokens.size()) {
            ok_multi = true;
            tests = move(tmp);
        }
    }

    if (ok_multi) {
        for (size_t i = 0; i < tests.size(); ++i) {
            cout << solve_single(tests[i]) << "\n";
        }
    } else {
        // Fallback: single test case
        vector<long long> arr;
        if (tokens.size() >= 2 && (size_t)(tokens[0]) + 1 <= tokens.size()) {
            long long n = tokens[0];
            size_t need = (size_t)n + 1;
            if (n >= 0 && need <= tokens.size()) {
                arr.assign(tokens.begin() + 1, tokens.begin() + 1 + n);
            } else {
                arr.assign(tokens.begin(), tokens.end());
            }
        } else if (tokens.size() >= 2) {
            long long n = tokens[0];
            if ((size_t)n + 1 <= tokens.size()) {
                arr.assign(tokens.begin() + 1, tokens.begin() + 1 + n);
            } else {
                arr.assign(tokens.begin(), tokens.end());
            }
        } else {
            arr.assign(tokens.begin(), tokens.end());
        }
        cout << solve_single(arr) << "\n";
    }

    return 0;
}