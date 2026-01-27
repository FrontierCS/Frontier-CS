#include <bits/stdc++.h>
using namespace std;

struct Index {
    vector<uint32_t> all;            // concatenated positions
    array<uint32_t, 37> off{};       // offsets per character (0..36)
};

static inline int charId(unsigned char c) {
    if (c >= '0' && c <= '9') return int(c - '0');
    return 10 + int(c - 'A'); // 'A'..'Z'
}

static Index buildIndex(const string& s) {
    array<uint32_t, 36> cnt{};
    cnt.fill(0);

    for (unsigned char c : s) ++cnt[charId(c)];

    Index idx;
    idx.off[0] = 0;
    for (int k = 0; k < 36; ++k) idx.off[k + 1] = idx.off[k] + cnt[k];

    idx.all.resize(idx.off[36]);

    array<uint32_t, 36> cur{};
    for (int k = 0; k < 36; ++k) cur[k] = idx.off[k];

    const uint32_t n = (uint32_t)s.size();
    for (uint32_t i = 0; i < n; ++i) {
        int k = charId((unsigned char)s[i]);
        idx.all[cur[k]++] = i;
    }

    return idx;
}

static string greedyScan(const string& scanStr, const Index& targetIdx, size_t targetLen) {
    array<uint32_t, 36> ptr{};
    array<uint32_t, 36> end{};
    for (int k = 0; k < 36; ++k) {
        ptr[k] = targetIdx.off[k];
        end[k] = targetIdx.off[k + 1];
    }

    string out;
    out.reserve(targetLen);

    int64_t curPos = -1;
    const size_t n = scanStr.size();
    const uint32_t* all = targetIdx.all.data();

    for (size_t i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)scanStr[i];
        int k = charId(c);
        uint32_t p = ptr[k];
        uint32_t e = end[k];

        while (p < e && (int64_t)all[p] <= curPos) ++p;
        if (p < e) {
            out.push_back((char)c);
            curPos = (int64_t)all[p];
            ++p;
        }
        ptr[k] = p;
    }

    return out;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!(cin >> s1)) return 0;
    if (!(cin >> s2)) return 0;

    // For speed, build index for the shorter string and scan the longer one.
    string ans;
    if (s1.size() <= s2.size()) {
        Index idx = buildIndex(s1);
        ans = greedyScan(s2, idx, s1.size());
    } else {
        Index idx = buildIndex(s2);
        ans = greedyScan(s1, idx, s2.size());
    }

    cout.write(ans.data(), (streamsize)ans.size());
    cout.put('\n');
    return 0;
}