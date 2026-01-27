#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s, t;
    if (!getline(cin, s)) return 0;
    if (!getline(cin, t)) t.clear();
    if (!s.empty() && s.back() == '\r') s.pop_back();
    if (!t.empty() && t.back() == '\r') t.pop_back();

    size_t n = s.size(), m = t.size();
    string out;
    out.reserve(n + m);

    // Estimate a global shift using sampling to better align the strings initially
    const int MAX_SHIFT = 512;
    size_t L = min(n, m);
    int bestShift = 0;
    if (L > 0) {
        size_t maxSamples = 10000; // cap the number of samples
        size_t step = L / maxSamples;
        if (step == 0) step = 1;
        vector<size_t> idxs;
        idxs.reserve((L + step - 1) / step);
        for (size_t i = 0; i < L; i += step) idxs.push_back(i);
        int shifts = min<int>(MAX_SHIFT, (int)m);
        shifts = min<int>(shifts, (int)n + MAX_SHIFT); // keep reasonable
        int low = -min<int>(MAX_SHIFT, (int)n);
        int high = min<int>(MAX_SHIFT, (int)m);
        int bestCnt = -1;
        for (int d = low; d <= high; ++d) {
            int cnt = 0;
            for (size_t idx : idxs) {
                long jpos = (long)idx + d;
                if (jpos < 0 || jpos >= (long)m) continue;
                if (s[idx] == t[(size_t)jpos]) ++cnt;
            }
            if (cnt > bestCnt) { bestCnt = cnt; bestShift = d; }
        }
    }
    // Apply initial shift
    size_t i = 0, j = 0;
    if (bestShift > 0) {
        size_t ins = min<size_t>(bestShift, m);
        out.append(ins, 'I');
        j += ins;
    } else if (bestShift < 0) {
        size_t del = min<size_t>((size_t)(-bestShift), n);
        out.append(del, 'D');
        i += del;
    }

    while (i < n && j < m) {
        if (s[i] == t[j]) {
            out.push_back('M');
            ++i; ++j;
            continue;
        }
        bool did = false;

        size_t remS = n - i, remT = m - j;

        // Prefer handling based on remaining lengths
        if (remT > remS) {
            if (j + 1 < m && s[i] == t[j + 1]) {
                out.push_back('I');
                ++j; did = true;
            }
        } else if (remS > remT) {
            if (i + 1 < n && s[i + 1] == t[j]) {
                out.push_back('D');
                ++i; did = true;
            }
        }

        if (!did) {
            // Try one-step indels
            if (i + 1 < n && s[i + 1] == t[j]) {
                out.push_back('D'); ++i; did = true;
            } else if (j + 1 < m && s[i] == t[j + 1]) {
                out.push_back('I'); ++j; did = true;
            }
        }

        if (!did) {
            // Try two-step indels if they help
            if (remT >= remS) {
                if (j + 2 < m && s[i] == t[j + 2]) {
                    out.push_back('I'); out.push_back('I'); j += 2; did = true;
                }
            }
            if (!did && remS >= remT) {
                if (i + 2 < n && s[i + 2] == t[j]) {
                    out.push_back('D'); out.push_back('D'); i += 2; did = true;
                }
            }
        }

        if (!did) {
            // Substitution (or mismatch treated as M)
            out.push_back('M');
            ++i; ++j;
        }
    }

    while (i < n) { out.push_back('D'); ++i; }
    while (j < m) { out.push_back('I'); ++j; }

    cout << out << '\n';
    return 0;
}