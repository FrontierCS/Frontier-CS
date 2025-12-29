#include <bits/stdc++.h>
using namespace std;

static bool isInteger(const string& s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '+' || s[0] == '-') {
        if (s.size() == 1) return false;
        i = 1;
    }
    for (; i < s.size(); ++i) {
        if (!isdigit(static_cast<unsigned char>(s[i]))) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> tokens;
    string tok;
    while (cin >> tok) tokens.push_back(tok);
    if (tokens.empty()) return 0;

    vector<long long> vals;
    vals.reserve(tokens.size());
    for (auto &s : tokens) {
        if (isInteger(s)) {
            try {
                long long x = stoll(s);
                vals.push_back(x);
            } catch (...) {
                // Ignore tokens that are not valid integers
            }
        }
    }
    if (vals.empty()) return 0;

    auto tryParseMulti = [&](vector<pair<int, vector<int>>>& tests)->bool{
        long long T = vals[0];
        if (T < 1) return false;
        size_t idx = 1;
        tests.clear();
        tests.reserve((size_t)T);
        for (long long t = 0; t < T; ++t) {
            if (idx >= vals.size()) return false;
            long long nll = vals[idx++];
            if (nll < 1 || nll > (long long)1e6) return false; // sanity
            int n = (int)nll;
            if (idx + (size_t)n > vals.size()) return false;
            vector<int> p(n+1);
            for (int i = 1; i <= n; ++i) {
                long long v = vals[idx++];
                if (v < 1 || v > n) return false; // sanity
                p[i] = (int)v;
            }
            tests.emplace_back(n, move(p));
        }
        if (idx != vals.size()) return false;
        return true;
    };

    vector<pair<int, vector<int>>> tests;
    if (!tryParseMulti(tests)) {
        // Try parse as one or multiple testcases without leading T
        tests.clear();
        size_t idx = 0;
        while (idx < vals.size()) {
            long long nll = vals[idx++];
            if (nll < 1 || nll > (long long)1e6) { tests.clear(); break; }
            int n = (int)nll;
            if (idx + (size_t)n > vals.size()) { tests.clear(); break; }
            vector<int> p(n+1);
            for (int i = 1; i <= n; ++i) {
                long long v = vals[idx++];
                if (v < 1 || v > n) { tests.clear(); break; }
                p[i] = (int)v;
            }
            if (tests.empty() || !tests.back().second.empty()) {
                tests.emplace_back(n, move(p));
            } else {
                tests.back() = {n, move(p)};
            }
        }
        if (tests.empty()) {
            return 0;
        }
    }

    // Output position of n for each test
    // Offline: just scan to find where value == n
    for (auto &tc : tests) {
        int n = tc.first;
        const vector<int>& p = tc.second;
        int pos = -1;
        for (int i = 1; i <= n; ++i) {
            if (p[i] == n) { pos = i; break; }
        }
        if (pos == -1) pos = 1; // fallback, should not happen for valid permutations
        cout << pos << "\n";
    }

    return 0;
}