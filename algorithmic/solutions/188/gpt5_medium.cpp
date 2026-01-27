#include <bits/stdc++.h>
using namespace std;

inline int charIndex(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return 26 + (c - '0');
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) s1.clear();
    if (!getline(cin, s2)) s2.clear();
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    // Decide which string to scan and which to build position index for
    bool targetIsS1 = (s1.size() <= s2.size());
    const string &tgt = targetIsS1 ? s1 : s2; // build positions for this (shorter)
    const string &src = targetIsS1 ? s2 : s1; // scan this (longer)

    // Count occurrences in target to reserve memory
    array<size_t, 36> cnt{};
    cnt.fill(0);
    for (char c : tgt) {
        int id = charIndex(c);
        if (id >= 0) cnt[id]++;
    }

    // Build position lists for target
    array<vector<int>, 36> pos;
    for (int i = 0; i < 36; ++i) pos[i].reserve(cnt[i]);
    for (int i = 0; i < (int)tgt.size(); ++i) {
        int id = charIndex(tgt[i]);
        if (id >= 0) pos[id].push_back(i);
    }

    // Free target string memory
    if (targetIsS1) { string().swap(s1); } else { string().swap(s2); }

    // Greedy matching
    array<int, 36> ptr{};
    ptr.fill(0);
    int last = -1;

    const size_t CHUNK = 1 << 20; // 1 MB buffer
    vector<char> outbuf;
    outbuf.reserve(CHUNK);

    for (char c : src) {
        int id = charIndex(c);
        if (id < 0) continue;
        auto &vec = pos[id];
        int p = ptr[id];
        while (p < (int)vec.size() && vec[p] <= last) ++p;
        if (p < (int)vec.size()) {
            outbuf.push_back(c);
            last = vec[p];
            ++p;
            if (outbuf.size() >= CHUNK) {
                cout.write(outbuf.data(), (streamsize)outbuf.size());
                outbuf.clear();
            }
        }
        ptr[id] = p;
    }

    if (!outbuf.empty()) {
        cout.write(outbuf.data(), (streamsize)outbuf.size());
        outbuf.clear();
    }
    cout << '\n';
    return 0;
}