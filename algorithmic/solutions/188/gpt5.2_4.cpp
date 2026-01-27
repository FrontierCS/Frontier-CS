#include <bits/stdc++.h>
using namespace std;

struct FastInput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, sz = 0;

    inline bool refill() {
        sz = fread(buf, 1, BUFSIZE, stdin);
        idx = 0;
        return sz > 0;
    }

    string readLine() {
        string s;
        while (true) {
            if (idx >= sz) {
                if (!refill()) break;
            }
            char* start = buf + idx;
            size_t rem = sz - idx;
            void* p = memchr(start, '\n', rem);
            if (p) {
                char* nl = (char*)p;
                size_t len = (size_t)(nl - start);
                if (len && start[len - 1] == '\r') --len;
                s.append(start, len);
                idx += (size_t)(nl - start) + 1;
                break;
            } else {
                s.append(start, rem);
                idx = sz;
            }
        }
        return s;
    }
};

static int charToId[128];
static char idToCharArr[36];

struct PosIndex {
    vector<uint32_t> pos;          // size = n
    array<uint32_t, 37> off{};     // off[c]..off[c+1)
};

static inline PosIndex buildPos(const string& s) {
    PosIndex P;
    const uint32_t n = (uint32_t)s.size();

    array<uint32_t, 36> freq{};
    freq.fill(0);
    for (unsigned char ch : s) ++freq[(uint32_t)charToId[ch]];

    P.off[0] = 0;
    for (int c = 0; c < 36; ++c) P.off[c + 1] = P.off[c] + freq[c];

    P.pos.resize(n);
    array<uint32_t, 36> wr{};
    for (int c = 0; c < 36; ++c) wr[c] = P.off[c];

    for (uint32_t i = 0; i < n; ++i) {
        int c = charToId[(unsigned char)s[i]];
        P.pos[wr[(uint32_t)c]++] = i;
    }
    return P;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int i = 0; i < 128; ++i) charToId[i] = -1;
    for (int i = 0; i < 10; ++i) {
        charToId[(unsigned char)('0' + i)] = i;
        idToCharArr[i] = (char)('0' + i);
    }
    for (int i = 0; i < 26; ++i) {
        charToId[(unsigned char)('A' + i)] = 10 + i;
        idToCharArr[10 + i] = (char)('A' + i);
    }

    FastInput in;
    string s1 = in.readLine();
    string s2 = in.readLine();

    const uint32_t n1 = (uint32_t)s1.size();
    const uint32_t n2 = (uint32_t)s2.size();

    PosIndex P1 = buildPos(s1);
    PosIndex P2 = buildPos(s2);

    array<uint32_t, 36> p1{};
    array<uint32_t, 36> p2{};
    p1.fill(0);
    p2.fill(0);

    string out;
    out.reserve((size_t)min(n1, n2));

    uint32_t i = 0, j = 0;
    while (i < n1 && j < n2) {
        if (s1[(size_t)i] == s2[(size_t)j]) {
            out.push_back(s1[(size_t)i]);
            ++i;
            ++j;
            continue;
        }

        uint32_t bestKey = UINT32_MAX;
        uint64_t bestSum = UINT64_MAX;
        int bestC = -1;
        uint32_t bestA = 0, bestB = 0;

        for (int c = 0; c < 36; ++c) {
            const uint32_t b1 = P1.off[c], e1 = P1.off[c + 1];
            const uint32_t b2 = P2.off[c], e2 = P2.off[c + 1];

            uint32_t &k1 = p1[c];
            while (b1 + k1 < e1 && P1.pos[b1 + k1] < i) ++k1;

            uint32_t &k2 = p2[c];
            while (b2 + k2 < e2 && P2.pos[b2 + k2] < j) ++k2;

            if (b1 + k1 >= e1 || b2 + k2 >= e2) continue;

            uint32_t a = P1.pos[b1 + k1];
            uint32_t b = P2.pos[b2 + k2];
            uint32_t key = (a > b) ? a : b;
            uint64_t sum = (uint64_t)a + (uint64_t)b;

            if (key < bestKey || (key == bestKey && sum < bestSum)) {
                bestKey = key;
                bestSum = sum;
                bestC = c;
                bestA = a;
                bestB = b;
            }
        }

        if (bestC < 0) break;

        out.push_back(idToCharArr[bestC]);
        i = bestA + 1;
        j = bestB + 1;
        ++p1[bestC];
        ++p2[bestC];
    }

    fwrite(out.data(), 1, out.size(), stdout);
    fputc('\n', stdout);
    return 0;
}