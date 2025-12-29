#include <bits/stdc++.h>
using namespace std;

pair<int,int> ask_except(int n, int a, int b) {
    vector<int> v;
    v.reserve(n - 2);
    for (int i = 1; i <= n; ++i) {
        if (i == a || i == b) continue;
        v.push_back(i);
    }
    cout << 0 << ' ' << v.size();
    for (int x : v) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    int m1, m2;
    if (!(cin >> m1 >> m2)) exit(0);
    if (m1 == -1 && m2 == -1) exit(0);
    return {m1, m2};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int M = n / 2;       // value of first global median
    int Mp = M + 1;      // value of second global median

    auto classify = [&](int val) -> int {
        // 0: L (<M), 1: M1 (==M), 2: M2 (==M+1), 3: H (>M+1)
        if (val < M) return 0;
        if (val == M) return 1;
        if (val == Mp) return 2;
        return 3;
    };

    int anchor0 = 1;

    bool seenFirstL = false;
    bool seenSecondH = false;
    int idxLH = -1;   // pair type (L,H)
    int idxM1H = -1;  // pair type (M1,H) for anchor L -> identifies M2
    int idxLM2 = -1;  // pair type (L,M2) for anchor H -> identifies M1

    // Stage 1: use anchor0 with all other indices
    for (int i = 1; i <= n; ++i) {
        if (i == anchor0) continue;
        auto res = ask_except(n, anchor0, i);
        int t1 = classify(res.first);
        int t2 = classify(res.second);

        if (t1 == 0) seenFirstL = true;
        if (t2 == 3) seenSecondH = true;

        if (t1 == 0 && t2 == 3) idxLH = i;      // (L,H)
        if (t1 == 1 && t2 == 3) idxM1H = i;     // (M1,H)
        if (t1 == 0 && t2 == 2) idxLM2 = i;     // (L,M2)
    }

    string anchorType;
    if (!seenFirstL) anchorType = "L";
    else if (!seenSecondH) anchorType = "H";
    else anchorType = "Mid";

    int ans1 = -1, ans2 = -1;

    if (anchorType == "Mid") {
        // anchor0 is one of the medians, other is unique idx with (L,H)
        ans1 = anchor0;
        ans2 = idxLH;
    } else if (anchorType == "L") {
        // anchor0 is L, unique idx with (M1,H) is M2
        int idxM2 = idxM1H;
        int newAnchor = idxM2;  // type M2
        int otherMedian = -1;   // M1

        for (int j = 1; j <= n; ++j) {
            if (j == newAnchor) continue;
            auto res = ask_except(n, newAnchor, j);
            int t1 = classify(res.first);
            int t2 = classify(res.second);
            if (t1 == 0 && t2 == 3) { // (L,H)
                otherMedian = j;
            }
        }
        ans1 = newAnchor;
        ans2 = otherMedian;
    } else { // anchorType == "H"
        // anchor0 is H, unique idx with (L,M2) is M1
        int idxM1 = idxLM2;
        int newAnchor = idxM1;  // type M1
        int otherMedian = -1;   // M2

        for (int j = 1; j <= n; ++j) {
            if (j == newAnchor) continue;
            auto res = ask_except(n, newAnchor, j);
            int t1 = classify(res.first);
            int t2 = classify(res.second);
            if (t1 == 0 && t2 == 3) { // (L,H)
                otherMedian = j;
            }
        }
        ans1 = newAnchor;
        ans2 = otherMedian;
    }

    if (ans1 == -1 || ans2 == -1) {
        // Fallback (should not happen)
        ans1 = 1;
        ans2 = 2;
    }

    if (ans1 > ans2) swap(ans1, ans2);
    cout << 1 << ' ' << ans1 << ' ' << ans2 << '\n';
    cout.flush();
    return 0;
}