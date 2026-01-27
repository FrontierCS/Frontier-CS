#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2 = "";
    
    int n = (int)s1.size();
    int m = (int)s2.size();
    
    // Character mapping: 'A'-'Z' -> 0..25, '0'-'9' -> 26..35
    int cmap[256];
    memset(cmap, -1, sizeof(cmap));
    for (int c = 'A'; c <= 'Z'; ++c) cmap[c] = c - 'A';
    for (int c = '0'; c <= '9'; ++c) cmap[c] = 26 + (c - '0');
    
    const size_t FLUSH_THRESHOLD = 8u * 1024u * 1024u;
    string out;
    out.reserve(1u << 20);
    auto flush_out = [&]() {
        if (!out.empty()) {
            cout << out;
            out.clear();
        }
    };
    auto emit_char = [&](char ch) {
        out.push_back(ch);
        if (out.size() >= FLUSH_THRESHOLD) flush_out();
    };
    auto emit_repeat = [&](char ch, int cnt) {
        if (cnt <= 0) return;
        // append in chunks to avoid massive temporary peaks
        const int CHUNK = 1 << 20; // 1M
        while (cnt > 0) {
            int t = min(cnt, CHUNK);
            out.append(t, ch);
            if (out.size() >= FLUSH_THRESHOLD) flush_out();
            cnt -= t;
        }
    };
    
    if (m > n) {
        // Only inserts allowed (no deletes)
        // Build positions for s2
        vector<int> freq(36, 0);
        for (int j = 0; j < m; ++j) {
            int id = cmap[(unsigned char)s2[j]];
            if (id >= 0) freq[id]++;
        }
        vector<vector<int>> pos(36);
        for (int id = 0; id < 36; ++id) pos[id].reserve(freq[id]);
        for (int j = 0; j < m; ++j) {
            int id = cmap[(unsigned char)s2[j]];
            if (id >= 0) pos[id].push_back(j);
        }
        vector<int> ptr(36, 0);
        int i = 0, j = 0;
        for (; i < n; ++i) {
            int id = cmap[(unsigned char)s1[i]];
            if (id >= 0) {
                int &p = ptr[id];
                auto &vec = pos[id];
                while (p < (int)vec.size() && vec[p] < j) ++p;
                if (p < (int)vec.size()) {
                    int matchPos = vec[p];
                    emit_repeat('I', matchPos - j);
                    emit_char('M');
                    j = matchPos + 1;
                    ++p;
                    continue;
                }
            }
            // No future match, substitute
            emit_char('M');
            ++j;
        }
        // Remaining inserts
        if (j < m) emit_repeat('I', m - j);
    } else if (n > m) {
        // Only deletes allowed (no inserts)
        // Build positions for s1
        vector<int> freq(36, 0);
        for (int i = 0; i < n; ++i) {
            int id = cmap[(unsigned char)s1[i]];
            if (id >= 0) freq[id]++;
        }
        vector<vector<int>> pos(36);
        for (int id = 0; id < 36; ++id) pos[id].reserve(freq[id]);
        for (int i = 0; i < n; ++i) {
            int id = cmap[(unsigned char)s1[i]];
            if (id >= 0) pos[id].push_back(i);
        }
        vector<int> ptr(36, 0);
        int i = 0, j = 0;
        for (; j < m; ++j) {
            int id = cmap[(unsigned char)s2[j]];
            if (id >= 0) {
                int &p = ptr[id];
                auto &vec = pos[id];
                while (p < (int)vec.size() && vec[p] < i) ++p;
                if (p < (int)vec.size()) {
                    int matchPos = vec[p];
                    emit_repeat('D', matchPos - i);
                    emit_char('M');
                    i = matchPos + 1;
                    ++p;
                    continue;
                }
            }
            // No future match, substitute
            emit_char('M');
            ++i;
        }
        // Remaining deletes
        if (i < n) emit_repeat('D', n - i);
    } else {
        // Same length: all M
        emit_repeat('M', n);
    }
    
    flush_out();
    cout << "\n";
    return 0;
}