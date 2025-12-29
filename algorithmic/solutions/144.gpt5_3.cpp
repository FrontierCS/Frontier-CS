#include <bits/stdc++.h>
using namespace std;

int n;

pair<int,int> query_exclude(int a, int b) {
    vector<int> idx;
    idx.reserve(n-2);
    for (int i = 1; i <= n; ++i) {
        if (i == a || i == b) continue;
        idx.push_back(i);
    }
    cout << 0 << " " << idx.size();
    for (int x : idx) cout << " " << x;
    cout << "\n";
    cout.flush();
    int m1, m2;
    if (!(cin >> m1 >> m2)) exit(0);
    return {m1, m2};
}

char typeFromPair(const pair<int,int>& pr, int n) {
    int L1 = n/2 - 1;
    int M1v = n/2;
    int M2v = n/2 + 1;
    int H2 = n/2 + 2;
    int a = pr.first, b = pr.second;
    if (a == L1 && b == M1v) return 'A';         // (n/2-1, n/2)
    if (a == M2v && b == H2) return 'B';         // (n/2+1, n/2+2)
    if (a == M1v && b == M2v) return 'C';        // (n/2, n/2+1)
    if (a == L1 && b == M2v) return 'D';         // (n/2-1, n/2+1)
    if (a == M1v && b == H2) return 'E';         // (n/2, n/2+2)
    if (a == L1 && b == H2) return 'F';          // (n/2-1, n/2+2)
    return 'X'; // unknown
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    // Try with r = 1
    int r = 1;
    vector<char> typ(n+1, '?');
    int otherMedian = -1;
    for (int i = 1; i <= n; ++i) if (i != r) {
        auto pr = query_exclude(r, i);
        char t = typeFromPair(pr, n);
        typ[i] = t;
        if (t == 'F') {
            // {r, i} are medians
            cout << 1 << " " << r << " " << i << "\n";
            cout.flush();
            return 0;
        }
    }

    bool seenA=false, seenB=false, seenC=false, seenD=false, seenE=false;
    for (int i = 1; i <= n; ++i) if (i != r) {
        if (typ[i] == 'A') seenA = true;
        else if (typ[i] == 'B') seenB = true;
        else if (typ[i] == 'C') seenC = true;
        else if (typ[i] == 'D') seenD = true;
        else if (typ[i] == 'E') seenE = true;
    }

    int idxM1 = -1, idxM2 = -1;

    if (seenB && seenC) {
        // r is low
        int anyHigh = -1;
        for (int i = 1; i <= n; ++i) if (i != r && typ[i] == 'C') { anyHigh = i; break; }
        // M2 is unique i with type E
        for (int i = 1; i <= n; ++i) if (i != r && typ[i] == 'E') { idxM2 = i; break; }
        // Find M1 among those with type B by pairing with anyHigh
        for (int i = 1; i <= n; ++i) if (i != r && typ[i] == 'B') {
            auto pr = query_exclude(i, anyHigh);
            char t = typeFromPair(pr, n);
            if (t == 'D') { idxM1 = i; break; }
        }
        if (idxM1 != -1 && idxM2 != -1) {
            cout << 1 << " " << idxM1 << " " << idxM2 << "\n";
            cout.flush();
            return 0;
        }
    } else if (seenA && seenC) {
        // r is high
        int anyLow = -1;
        for (int i = 1; i <= n; ++i) if (i != r && typ[i] == 'C') { anyLow = i; break; }
        // M1 is unique i with type D
        for (int i = 1; i <= n; ++i) if (i != r && typ[i] == 'D') { idxM1 = i; break; }
        // Find M2 among those with type A by pairing with anyLow
        for (int i = 1; i <= n; ++i) if (i != r && typ[i] == 'A') {
            auto pr = query_exclude(i, anyLow);
            char t = typeFromPair(pr, n);
            if (t == 'E') { idxM2 = i; break; }
        }
        if (idxM1 != -1 && idxM2 != -1) {
            cout << 1 << " " << idxM1 << " " << idxM2 << "\n";
            cout.flush();
            return 0;
        }
    } else {
        // If r is one of the medians, we should have found 'F' earlier. As a fallback, try another r.
        for (r = 2; r <= n; ++r) {
            vector<char> typ2(n+1, '?');
            bool foundF = false;
            for (int i = 1; i <= n; ++i) if (i != r) {
                auto pr = query_exclude(r, i);
                char t = typeFromPair(pr, n);
                typ2[i] = t;
                if (t == 'F') {
                    cout << 1 << " " << r << " " << i << "\n";
                    cout.flush();
                    return 0;
                }
            }
            bool A=false,B=false,C=false,D=false,E=false;
            for (int i = 1; i <= n; ++i) if (i != r) {
                if (typ2[i]=='A') A=true; else if (typ2[i]=='B') B=true;
                else if (typ2[i]=='C') C=true; else if (typ2[i]=='D') D=true;
                else if (typ2[i]=='E') E=true;
            }
            if (B && C) {
                // r low
                int anyHigh = -1;
                int m2 = -1, m1 = -1;
                for (int i = 1; i <= n; ++i) if (i != r && typ2[i] == 'C') { anyHigh = i; break; }
                for (int i = 1; i <= n; ++i) if (i != r && typ2[i] == 'E') { m2 = i; break; }
                for (int i = 1; i <= n; ++i) if (i != r && typ2[i] == 'B') {
                    auto pr = query_exclude(i, anyHigh);
                    char t = typeFromPair(pr, n);
                    if (t == 'D') { m1 = i; break; }
                }
                if (m1 != -1 && m2 != -1) {
                    cout << 1 << " " << m1 << " " << m2 << "\n";
                    cout.flush();
                    return 0;
                }
            } else if (A && C) {
                // r high
                int anyLow = -1;
                int m1 = -1, m2 = -1;
                for (int i = 1; i <= n; ++i) if (i != r && typ2[i] == 'C') { anyLow = i; break; }
                for (int i = 1; i <= n; ++i) if (i != r && typ2[i] == 'D') { m1 = i; break; }
                for (int i = 1; i <= n; ++i) if (i != r && typ2[i] == 'A') {
                    auto pr = query_exclude(i, anyLow);
                    char t = typeFromPair(pr, n);
                    if (t == 'E') { m2 = i; break; }
                }
                if (m1 != -1 && m2 != -1) {
                    cout << 1 << " " << m1 << " " << m2 << "\n";
                    cout.flush();
                    return 0;
                }
            }
        }
    }

    // Fallback (should not happen): output two indices to avoid runtime error.
    // We attempt to find with brute-force pairs (exclude) looking for 'F'.
    for (int i = 1; i <= n; ++i) for (int j = i+1; j <= n; ++j) {
        auto pr = query_exclude(i, j);
        char t = typeFromPair(pr, n);
        if (t == 'F') {
            cout << 1 << " " << i << " " << j << "\n";
            cout.flush();
            return 0;
        }
    }

    return 0;
}