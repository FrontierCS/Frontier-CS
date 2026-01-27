#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> a;
    long long v;
    while (cin >> v) a.push_back(v);
    
    if (a.empty()) return 0;

    vector<long long> ans;
    bool parsed = false;

    // Try parse format: T, then T testcases each: n followed by permutation of size n
    {
        long long T = a[0];
        long long pos = 1;
        bool ok = true;
        vector<long long> tmp;
        for (long long t = 0; t < T; ++t) {
            if (pos >= (long long)a.size()) { ok = false; break; }
            long long n = a[pos++];
            if (n < 0 || pos + n > (long long)a.size()) { ok = false; break; }
            long long idx = -1;
            for (long long i = 0; i < n; ++i) {
                if (a[pos + i] == n) idx = i + 1; // 1-indexed
            }
            pos += n;
            if (idx == -1) {
                long long mx = LLONG_MIN;
                long long maxpos = -1;
                for (long long i = 0; i < n; ++i) {
                    long long val = a[pos - n + i];
                    if (val > mx) { mx = val; maxpos = i + 1; }
                }
                idx = maxpos;
            }
            tmp.push_back(idx);
        }
        if (ok && pos == (long long)a.size()) {
            parsed = true;
            ans = move(tmp);
        }
    }

    // Try parse format: single test case: n followed by permutation of size n
    if (!parsed) {
        long long n = a[0];
        if (n >= 0 && (long long)a.size() == 1 + n) {
            long long idx = -1;
            for (long long i = 0; i < n; ++i) {
                if (a[1 + i] == n) idx = i + 1;
            }
            if (idx == -1) {
                long long mx = LLONG_MIN, mp = -1;
                for (long long i = 0; i < n; ++i) {
                    if (a[1 + i] > mx) { mx = a[1 + i]; mp = i + 1; }
                }
                idx = mp;
            }
            parsed = true;
            ans.push_back(idx);
        }
    }

    // Try parse format: multiple test cases without T: repeating blocks of n and permutation
    if (!parsed) {
        long long pos = 0;
        vector<long long> tmp;
        bool ok = true;
        while (pos < (long long)a.size()) {
            long long n = a[pos++];
            if (n < 0 || pos + n > (long long)a.size()) { ok = false; break; }
            long long idx = -1;
            for (long long i = 0; i < n; ++i) {
                if (a[pos + i] == n) idx = i + 1;
            }
            pos += n;
            if (idx == -1) {
                long long mx = LLONG_MIN, mp = -1;
                for (long long i = 0; i < n; ++i) {
                    long long val = a[pos - n + i];
                    if (val > mx) { mx = val; mp = i + 1; }
                }
                idx = mp;
            }
            tmp.push_back(idx);
        }
        if (ok && pos == (long long)a.size()) {
            parsed = true;
            ans = move(tmp);
        }
    }

    if (parsed) {
        for (size_t i = 0; i < ans.size(); ++i) {
            cout << ans[i] << (i + 1 < ans.size() ? '\n' : '\n');
        }
    }

    return 0;
}