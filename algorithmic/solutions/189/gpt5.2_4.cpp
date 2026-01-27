#include <bits/stdc++.h>
using namespace std;

static inline int chIdx(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return 10 + (c - 'A');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();

    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    int n = (int)s1.size();
    int m = (int)s2.size();

    if (n == 0 && m == 0) {
        cout << "\n";
        return 0;
    }
    if (n == 0) {
        cout << string(m, 'I') << "\n";
        return 0;
    }
    if (m == 0) {
        cout << string(n, 'D') << "\n";
        return 0;
    }

    array<int, 36> freq{};
    for (int j = 0; j < m; ++j) freq[chIdx(s2[j])]++;

    vector<vector<int>> pos2(36);
    for (int c = 0; c < 36; ++c) pos2[c].reserve(freq[c]);
    for (int j = 0; j < m; ++j) pos2[chIdx(s2[j])].push_back(j);

    size_t range = (size_t)n + (size_t)m + 1;
    vector<uint16_t> cnt(range, 0);

    int bestOff = 0;
    uint16_t bestCnt = 0;

    auto addOffset = [&](int off) {
        if (off < -n) return;
        if (off > m) return;
        size_t id = (size_t)(off + n);
        uint16_t v = cnt[id];
        if (v != 65535) ++v;
        cnt[id] = v;
        if (v > bestCnt) {
            bestCnt = v;
            bestOff = off;
        }
    };

    int Ktarget = 20000;
    int K = min(Ktarget, n);
    int step = n / K;
    if (step <= 0) step = 1;

    int samples = 0;
    for (int i = 0; i < n && samples < K; i += step, ++samples) {
        int c = chIdx(s1[i]);
        const auto &vec = pos2[c];
        if (vec.empty()) continue;

        int j0 = (int)((long long)i * m / n);

        auto it = lower_bound(vec.begin(), vec.end(), j0);
        if (it != vec.end()) addOffset(*it - i);
        if (it != vec.begin()) {
            auto it2 = it;
            --it2;
            addOffset(*it2 - i);
        }
        if (it != vec.end()) {
            auto it3 = it;
            ++it3;
            if (it3 != vec.end()) addOffset(*it3 - i);
        }
    }

    if (bestCnt < 3) bestOff = 0;
    if (bestOff < -n) bestOff = -n;
    if (bestOff > m) bestOff = m;

    string out;
    out.reserve((size_t)n + (size_t)m);

    int i = 0, j = 0;
    if (bestOff > 0) {
        int k = min(bestOff, m);
        out.append((size_t)k, 'I');
        j += k;
    } else if (bestOff < 0) {
        int k = min(-bestOff, n);
        out.append((size_t)k, 'D');
        i += k;
    }

    const char *a = s1.data();
    const char *b = s2.data();
    const int W = 8;

    while (i < n && j < m) {
        if (a[i] == b[j]) {
            out.push_back('M');
            ++i; ++j;
            continue;
        }

        int bestDel = 0, bestIns = 0;

        int maxDel = n - i - 1;
        if (maxDel > W) maxDel = W;
        for (int t = 1; t <= maxDel; ++t) {
            if (a[i + t] == b[j]) { bestDel = t; break; }
        }

        int maxIns = m - j - 1;
        if (maxIns > W) maxIns = W;
        for (int t = 1; t <= maxIns; ++t) {
            if (b[j + t] == a[i]) { bestIns = t; break; }
        }

        if (bestDel && (!bestIns || bestDel < bestIns || (bestDel == bestIns && (n - i) > (m - j)))) {
            out.append((size_t)bestDel, 'D');
            i += bestDel;
        } else if (bestIns) {
            out.append((size_t)bestIns, 'I');
            j += bestIns;
        } else {
            out.push_back('M');
            ++i; ++j;
        }
    }

    if (i < n) out.append((size_t)(n - i), 'D');
    if (j < m) out.append((size_t)(m - j), 'I');

    cout.write(out.data(), (streamsize)out.size());
    cout.put('\n');
    return 0;
}