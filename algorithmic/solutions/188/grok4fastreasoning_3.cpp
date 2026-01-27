#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string S1, S2;
    cin >> S1 >> S2;
    size_t N = S1.size();
    size_t M = S2.size();

    // First, build pos for S2 and compute Z1 iterating S1
    vector<vector<int>> pos(128);
    for (int j = 0; j < M; ++j) {
        unsigned char c = S2[j];
        pos[c].push_back(j);
    }
    string z1;
    int ptr1[128] = {};
    int current1 = -1;
    for (size_t i = 0; i < N; ++i) {
        unsigned char c = S1[i];
        auto& p = pos[c];
        int& idx = ptr1[c];
        while (idx < (int)p.size() && p[idx] <= current1) ++idx;
        if (idx < (int)p.size()) {
            z1 += S1[i];
            current1 = p[idx];
            ++idx;
        }
    }

    // Clear pos
    for (auto& v : pos) v.clear();

    // Now build pos for S1 and compute Z2 iterating S2
    for (int j = 0; j < N; ++j) {
        unsigned char c = S1[j];
        pos[c].push_back(j);
    }
    string z2;
    int ptr2[128] = {};
    int current2 = -1;
    for (size_t i = 0; i < M; ++i) {
        unsigned char c = S2[i];
        auto& p = pos[c];
        int& idx = ptr2[c];
        while (idx < (int)p.size() && p[idx] <= current2) ++idx;
        if (idx < (int)p.size()) {
            z2 += S2[i];
            current2 = p[idx];
            ++idx;
        }
    }

    // Output the longer one
    if (z1.size() >= z2.size()) {
        cout << z1 << '\n';
    } else {
        cout << z2 << '\n';
    }
    return 0;
}