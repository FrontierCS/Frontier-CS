#include <bits/stdc++.h>
using namespace std;

struct FastInput {
    static const size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, len = 0;
    inline bool refill() {
        len = fread(buf, 1, BUFSIZE, stdin);
        idx = 0;
        return len > 0;
    }
    inline bool getChar(char &c) {
        if (idx >= len) {
            if (!refill()) return false;
        }
        c = buf[idx++];
        return true;
    }
    bool readLine(string &out) {
        out.clear();
        char c;
        bool any = false;
        while (getChar(c)) {
            any = true;
            if (c == '\n') break;
            if (c != '\r') out.push_back(c);
        }
        return any;
    }
};

static inline int charIdx(char c) {
    unsigned char uc = (unsigned char)c;
    if (uc >= 'A' && uc <= 'Z') return uc - 'A';
    if (uc >= '0' && uc <= '9') return 26 + (uc - '0');
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastInput in;
    string s1, s2;
    if (!in.readLine(s1)) return 0;
    in.readLine(s2);

    const int K = 36;
    array<vector<uint32_t>, K> pos1, pos2;

    uint32_t n1 = (uint32_t)s1.size();
    uint32_t n2 = (uint32_t)s2.size();

    for (uint32_t i = 0; i < n1; ++i) {
        int id = charIdx(s1[i]);
        if (id >= 0) pos1[id].push_back(i);
    }
    for (uint32_t j = 0; j < n2; ++j) {
        int id = charIdx(s2[j]);
        if (id >= 0) pos2[id].push_back(j);
    }

    // Embed s1 into s2
    string ret1; ret1.reserve(min(n1, n2));
    array<uint32_t, K> ptr2{};
    ptr2.fill(0);
    int64_t pos = -1;
    for (uint32_t i = 0; i < n1; ++i) {
        int id = charIdx(s1[i]);
        if (id < 0) continue;
        auto &v = pos2[id];
        uint32_t &p = ptr2[id];
        while (p < v.size() && (int64_t)v[p] <= pos) ++p;
        if (p < v.size()) {
            ret1.push_back(s1[i]);
            pos = v[p];
            ++p;
        }
    }

    // Embed s2 into s1
    string ret2; ret2.reserve(min(n1, n2));
    array<uint32_t, K> ptr1{};
    ptr1.fill(0);
    pos = -1;
    for (uint32_t j = 0; j < n2; ++j) {
        int id = charIdx(s2[j]);
        if (id < 0) continue;
        auto &v = pos1[id];
        uint32_t &p = ptr1[id];
        while (p < v.size() && (int64_t)v[p] <= pos) ++p;
        if (p < v.size()) {
            ret2.push_back(s2[j]);
            pos = v[p];
            ++p;
        }
    }

    const string &ans = (ret1.size() >= ret2.size() ? ret1 : ret2);
    fwrite(ans.data(), 1, ans.size(), stdout);
    fwrite("\n", 1, 1, stdout);
    return 0;
}