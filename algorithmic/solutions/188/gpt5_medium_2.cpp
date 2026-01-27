#include <bits/stdc++.h>
using namespace std;

inline int mapChar(unsigned char ch) {
    if (ch >= '0' && ch <= '9') return ch - '0';
    return 10 + (ch - 'A');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string A, B;
    if (!getline(cin, A)) A.clear();
    if (!getline(cin, B)) B.clear();

    // Choose S as longer string to scan, T as shorter to build positions on
    bool a_longer = A.size() >= B.size();
    string &S = a_longer ? A : B;      // longer
    string &Tref = a_longer ? B : A;   // shorter
    string T = std::move(Tref);        // free the original reference

    const size_t Ts = T.size();

    // Count frequencies in T to reserve
    array<size_t, 36> cnt{};
    for (unsigned char ch : T) cnt[mapChar(ch)]++;

    // Build position lists for T
    array<vector<int>, 36> pos;
    for (int i = 0; i < 36; ++i) pos[i].reserve(cnt[i]);
    for (int i = 0; i < (int)Ts; ++i) {
        unsigned char ch = (unsigned char)T[i];
        pos[mapChar(ch)].push_back(i);
    }

    // Free T memory
    T.clear();
    T.shrink_to_fit();

    // Prepare scanning S against T positions
    array<int, 36> ptr{};
    int j = 0;
    string ans;
    ans.reserve(Ts);

    for (unsigned char ch : S) {
        int idx = mapChar(ch);
        auto &v = pos[idx];
        int &p = ptr[idx];
        while (p < (int)v.size() && v[p] < j) ++p;
        if (p < (int)v.size()) {
            ans.push_back((char)ch);
            j = v[p] + 1;
            ++p;
            if (j >= (int)Ts) break;
        }
    }

    // Output result
    cout.write(ans.data(), (streamsize)ans.size());
    cout.put('\n');
    return 0;
}