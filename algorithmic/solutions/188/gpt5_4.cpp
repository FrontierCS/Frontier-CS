#include <bits/stdc++.h>
using namespace std;

static inline int char_id(unsigned char ch) {
    if (ch >= 'A' && ch <= 'Z') return ch - 'A';
    else return 26 + (ch - '0'); // '0'..'9'
}

const int ALPH = 36;

size_t greedy_forward_length(const string& s1, const vector<vector<int>>& pos2) {
    int M = (int)(pos2.empty() ? 0 : 0); // to avoid unused warning
    (void)M;
    int p2[ALPH]; memset(p2, 0, sizeof(p2));
    int j = 0;
    size_t len = 0;
    // Determine M from any list or from context is not needed; we use comparisons with j.
    for (int i = 0; i < (int)s1.size(); ++i) {
        int c = char_id((unsigned char)s1[i]);
        auto &v = pos2[c];
        int &p = p2[c];
        while (p < (int)v.size() && v[p] < j) ++p;
        if (p >= (int)v.size()) continue;
        ++len;
        j = v[p] + 1;
        ++p;
    }
    return len;
}

void greedy_forward_print(const string& s1, const vector<vector<int>>& pos2) {
    int p2[ALPH]; memset(p2, 0, sizeof(p2));
    int j = 0;
    string out;
    out.reserve(1<<20);
    for (int i = 0; i < (int)s1.size(); ++i) {
        int c = char_id((unsigned char)s1[i]);
        auto &v = pos2[c];
        int &p = p2[c];
        while (p < (int)v.size() && v[p] < j) ++p;
        if (p >= (int)v.size()) continue;
        out.push_back(s1[i]);
        if (out.size() >= (1<<20)) {
            cout.write(out.data(), out.size());
            out.clear();
        }
        j = v[p] + 1;
        ++p;
    }
    if (!out.empty()) {
        cout.write(out.data(), out.size());
        out.clear();
    }
}

size_t greedy_twoptr_lookahead_length(const string& s1, const string& s2,
                                      const vector<vector<int>>& pos1,
                                      const vector<vector<int>>& pos2) {
    int N = (int)s1.size(), M = (int)s2.size();
    int ptr1[ALPH], ptr2[ALPH];
    memset(ptr1, 0, sizeof(ptr1));
    memset(ptr2, 0, sizeof(ptr2));
    int i = 0, j = 0;
    size_t len = 0;
    const int INF = INT_MAX/2;
    while (i < N && j < M) {
        if (s1[i] == s2[j]) {
            ++i; ++j; ++len;
            continue;
        }
        int c1 = char_id((unsigned char)s1[i]);
        int c2 = char_id((unsigned char)s2[j]);

        // Next in s2 for s1[i]
        int &p2c = ptr2[c1];
        const auto &v2 = pos2[c1];
        while (p2c < (int)v2.size() && v2[p2c] < j) ++p2c;
        int jnext = (p2c < (int)v2.size() ? v2[p2c] : INF);

        // Next in s1 for s2[j]
        int &p1c = ptr1[c2];
        const auto &v1 = pos1[c2];
        while (p1c < (int)v1.size() && v1[p1c] < i) ++p1c;
        int inext = (p1c < (int)v1.size() ? v1[p1c] : INF);

        if (jnext == INF && inext == INF) {
            ++i; ++j;
        } else if (jnext == INF) {
            ++i; // s1[i] cannot be matched later in s2, drop it
        } else if (inext == INF) {
            ++j; // s2[j] cannot be matched later in s1, drop it
        } else {
            if ((jnext - j) <= (inext - i)) {
                j = jnext; // align s1[i] with s2[jnext], match in next iteration
            } else {
                i = inext; // align s2[j] with s1[inext]
            }
        }
    }
    return len;
}

void greedy_twoptr_lookahead_print(const string& s1, const string& s2,
                                   const vector<vector<int>>& pos1,
                                   const vector<vector<int>>& pos2) {
    int N = (int)s1.size(), M = (int)s2.size();
    int ptr1[ALPH], ptr2[ALPH];
    memset(ptr1, 0, sizeof(ptr1));
    memset(ptr2, 0, sizeof(ptr2));
    int i = 0, j = 0;
    string out;
    out.reserve(1<<20);
    const int INF = INT_MAX/2;
    while (i < N && j < M) {
        if (s1[i] == s2[j]) {
            out.push_back(s1[i]);
            if (out.size() >= (1<<20)) {
                cout.write(out.data(), out.size());
                out.clear();
            }
            ++i; ++j;
            continue;
        }
        int c1 = char_id((unsigned char)s1[i]);
        int c2 = char_id((unsigned char)s2[j]);

        int &p2c = ptr2[c1];
        const auto &v2 = pos2[c1];
        while (p2c < (int)v2.size() && v2[p2c] < j) ++p2c;
        int jnext = (p2c < (int)v2.size() ? v2[p2c] : INF);

        int &p1c = ptr1[c2];
        const auto &v1 = pos1[c2];
        while (p1c < (int)v1.size() && v1[p1c] < i) ++p1c;
        int inext = (p1c < (int)v1.size() ? v1[p1c] : INF);

        if (jnext == INF && inext == INF) {
            ++i; ++j;
        } else if (jnext == INF) {
            ++i;
        } else if (inext == INF) {
            ++j;
        } else {
            if ((jnext - j) <= (inext - i)) {
                j = jnext;
            } else {
                i = inext;
            }
        }
    }
    if (!out.empty()) {
        cout.write(out.data(), out.size());
        out.clear();
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) {
        cout << "\n";
        return 0;
    }
    if (!getline(cin, s2)) s2.clear();

    // Frequency counts
    vector<int> cnt1(ALPH, 0), cnt2(ALPH, 0);
    for (char ch : s1) cnt1[char_id((unsigned char)ch)]++;
    for (char ch : s2) cnt2[char_id((unsigned char)ch)]++;

    // Best single-character fallback
    int bestChar = 0;
    long long bestSingle = 0;
    for (int c = 0; c < ALPH; ++c) {
        long long val = min(cnt1[c], cnt2[c]);
        if (val > bestSingle) { bestSingle = val; bestChar = c; }
    }

    // Build positions lists
    vector<vector<int>> pos1(ALPH), pos2(ALPH);
    for (int c = 0; c < ALPH; ++c) {
        if (cnt1[c]) pos1[c].reserve(cnt1[c]);
        if (cnt2[c]) pos2[c].reserve(cnt2[c]);
    }
    for (int i = 0; i < (int)s1.size(); ++i) pos1[char_id((unsigned char)s1[i])].push_back(i);
    for (int j = 0; j < (int)s2.size(); ++j) pos2[char_id((unsigned char)s2[j])].push_back(j);

    // Compute candidate lengths
    size_t lenA = greedy_forward_length(s1, pos2);
    size_t lenB = greedy_forward_length(s2, pos1); // subseq of s2 also subseq of s1
    size_t lenC = greedy_twoptr_lookahead_length(s1, s2, pos1, pos2);
    size_t lenD = (size_t)bestSingle;

    // Choose best
    // Priority: C, then A, then B, then D (on ties, prefer earlier)
    size_t bestLen = lenC;
    int bestAlg = 2; // 0:A, 1:B, 2:C, 3:D
    if (lenA > bestLen) { bestLen = lenA; bestAlg = 0; }
    if (lenB > bestLen) { bestLen = lenB; bestAlg = 1; }
    if (lenD > bestLen) { bestLen = lenD; bestAlg = 3; }

    // Output chosen result
    if (bestAlg == 2) {
        greedy_twoptr_lookahead_print(s1, s2, pos1, pos2);
    } else if (bestAlg == 0) {
        greedy_forward_print(s1, pos2);
    } else if (bestAlg == 1) {
        greedy_forward_print(s2, pos1);
    } else {
        // Print best single character repeated
        char outc;
        if (bestChar < 26) outc = (char)('A' + bestChar);
        else outc = (char)('0' + (bestChar - 26));
        const size_t CHUNK = 1 << 20;
        string chunk;
        chunk.assign(min(bestLen, CHUNK), outc);
        size_t remain = bestLen;
        while (remain > 0) {
            size_t w = min(remain, CHUNK);
            if (chunk.size() != w) chunk.assign(w, outc);
            cout.write(chunk.data(), w);
            remain -= w;
        }
    }
    cout << "\n";
    return 0;
}