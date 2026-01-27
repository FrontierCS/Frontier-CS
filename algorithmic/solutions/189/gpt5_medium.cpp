#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    const int K = 36;
    auto idxOf = [](char c)->int {
        if (c >= 'A' && c <= 'Z') return c - 'A';
        if (c >= '0' && c <= '9') return 26 + (c - '0');
        return 0;
    };

    const long long N = (long long)s1.size();
    const long long M = (long long)s2.size();

    // Precompute positions of each character in s2
    vector<int> freq(K, 0);
    for (char c : s2) freq[idxOf(c)]++;
    vector<vector<int>> pos(K);
    for (int i = 0; i < K; ++i) pos[i].reserve(freq[i]);
    for (int j = 0; j < (int)M; ++j) pos[idxOf(s2[j])].push_back(j);

    vector<int> p(K, 0);

    const size_t CHUNK = 4u << 20; // 4MB
    string out;
    out.reserve(CHUNK);

    auto flush = [&]() {
        if (!out.empty()) {
            cout.write(out.data(), out.size());
            out.clear();
        }
    };
    auto emitRepeat = [&](char c, long long cnt) {
        while (cnt > 0) {
            size_t space = CHUNK - out.size();
            if (space == 0) { flush(); space = CHUNK; }
            size_t toadd = (size_t)min<long long>(cnt, (long long)space);
            out.append(toadd, c);
            cnt -= toadd;
        }
    };

    long long last_i = -1, last_j = -1;

    auto processGap = [&](long long next_i, long long next_j) {
        long long Lgap = next_i - last_i - 1;
        long long Kg = next_j - last_j - 1;
        if (Lgap < 0) Lgap = 0;
        if (Kg < 0) Kg = 0;
        long long s = (Lgap < Kg) ? Lgap : Kg;
        if (s > 0) emitRepeat('M', s);
        if (Lgap > Kg) emitRepeat('D', Lgap - Kg);
        else if (Kg > Lgap) emitRepeat('I', Kg - Lgap);
        last_i = next_i - 1;
        last_j = next_j - 1;
    };

    for (long long i = 0; i < N; ++i) {
        int idx = idxOf(s1[(size_t)i]);
        auto &vec = pos[idx];
        int &pp = p[idx];
        while (pp < (int)vec.size() && (long long)vec[pp] <= last_j) ++pp;
        if (pp < (int)vec.size()) {
            long long jpos = vec[pp++];
            processGap(i, jpos);
            emitRepeat('M', 1);
            last_i = i;
            last_j = jpos;
        }
    }

    processGap(N, M);

    flush();
    cout.put('\n');
    return 0;
}