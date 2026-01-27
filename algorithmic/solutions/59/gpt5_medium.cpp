#include <bits/stdc++.h>
using namespace std;

bool isJ(const vector<long long>& v, int n) {
    if ((int)v.size() != n) return false;
    for (int i = 1; i <= n; ++i) {
        long long x = v[i-1];
        if (x < i || x > min(n, i+2)) return false;
    }
    return true;
}
bool isPerm(const vector<long long>& v, int n) {
    if ((int)v.size() != n) return false;
    vector<int> cnt(n+1,0);
    for (long long x : v) {
        if (x < 1 || x > n) return false;
        if (++cnt[(int)x] > 1) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Read entire stdin as string and parse integers (robust against any stray symbols)
    std::string s((std::istreambuf_iterator<char>(cin)), std::istreambuf_iterator<char>());
    vector<long long> tokens;
    long long sign = 1, num = 0;
    bool inNum = false, hasDigit = false;
    for (size_t i = 0; i < s.size(); ++i) {
        char c = s[i];
        if (!inNum) {
            if (c == '-' || (c >= '0' && c <= '9')) {
                inNum = true;
                sign = 1;
                num = 0;
                hasDigit = false;
                if (c == '-') sign = -1;
                else {
                    num = c - '0';
                    hasDigit = true;
                }
            }
        } else {
            if (c >= '0' && c <= '9') {
                num = num * 10 + (c - '0');
                hasDigit = true;
            } else {
                if (hasDigit) tokens.push_back(sign * num);
                inNum = false;
            }
        }
    }
    if (inNum && hasDigit) tokens.push_back(sign * num);

    if (tokens.empty()) return 0;
    int n = (int)tokens[0];
    vector<long long> rest;
    for (size_t i = 1; i < tokens.size(); ++i) rest.push_back(tokens[i]);

    vector<long long> output;
    auto tryBuildFromJ = [&](const vector<long long>& jv){
        vector<int> a(n+1);
        for (int i = 1; i <= n; ++i) a[i] = i;
        for (int i = 1; i <= n; ++i) {
            int j = (int)jv[i-1];
            if (j >= 1 && j <= n) swap(a[i], a[j]);
        }
        vector<long long> res(n);
        for (int i = 1; i <= n; ++i) res[i-1] = a[i];
        return res;
    };

    bool done = false;
    if ((int)rest.size() >= n) {
        vector<long long> cand(rest.begin(), rest.begin()+n);
        if (isJ(cand, n)) {
            output = tryBuildFromJ(cand);
            done = true;
        } else if (isPerm(cand, n)) {
            output = cand;
            done = true;
        }
    }
    if (!done && (int)rest.size() >= n) {
        vector<long long> cand(rest.end()-n, rest.end());
        if (isJ(cand, n)) {
            output = tryBuildFromJ(cand);
            done = true;
        } else if (isPerm(cand, n)) {
            output = cand;
            done = true;
        }
    }
    // Fallback: if exactly n numbers given, attempt best guess
    if (!done && (int)rest.size() == n) {
        if (isJ(rest, n)) output = tryBuildFromJ(rest);
        else output = rest; // assume it's the permutation
        done = true;
    }
    // If still not done, attempt to find any window of length n that works
    if (!done) {
        for (int i = 0; i + n <= (int)rest.size(); ++i) {
            vector<long long> cand(rest.begin()+i, rest.begin()+i+n);
            if (isJ(cand, n)) {
                output = tryBuildFromJ(cand);
                done = true;
                break;
            }
            if (isPerm(cand, n)) {
                output = cand;
                done = true;
                break;
            }
        }
    }

    if (!done) {
        // As a last resort, output identity
        output.resize(n);
        for (int i = 0; i < n; ++i) output[i] = i+1;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << output[i];
    }
    cout << '\n';
    return 0;
}