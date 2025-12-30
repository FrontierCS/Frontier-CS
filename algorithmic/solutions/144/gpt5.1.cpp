#include <bits/stdc++.h>
using namespace std;

int n;
int vL, vH;

pair<int,int> do_query(const vector<int>& S) {
    cout << "0 " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();

    int a, b;
    if (!(cin >> a >> b)) exit(0);
    return {a, b};
}

char classify_pair(int i, int j) {
    vector<int> S;
    S.reserve(n - 2);
    for (int x = 1; x <= n; ++x) {
        if (x != i && x != j) S.push_back(x);
    }
    auto res = do_query(S);
    int a = res.first, b = res.second;

    if (a == vL && b == vH) return 'A';
    if (b == vL) return 'B';
    if (a == vL) return 'C';
    if (b == vH) return 'D';
    if (a == vH) return 'E';
    return 'F'; // a < vL && b > vH
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    vL = n / 2;
    vH = vL + 1;

    int anchor = 1;
    int idxF = -1, idxC = -1, idxD = -1;

    for (int i = 2; i <= n; ++i) {
        char t = classify_pair(anchor, i);
        if (t == 'F') idxF = i;
        else if (t == 'C') idxC = i;
        else if (t == 'D') idxD = i;
    }

    int ans1 = -1, ans2 = -1;

    if (idxF != -1) {
        // anchor is median, partner is idxF
        ans1 = anchor;
        ans2 = idxF;
    } else if (idxC != -1) {
        // anchor in L, idxC is HM
        int anchor2 = idxC; // HM
        int partner = -1;
        for (int i = 1; i <= n; ++i) {
            if (i == anchor2) continue;
            char t = classify_pair(anchor2, i);
            if (t == 'F') {
                partner = i; // LM
                break;
            }
        }
        ans1 = anchor2;
        ans2 = partner;
    } else if (idxD != -1) {
        // anchor in R, idxD is LM
        int anchor2 = idxD; // LM
        int partner = -1;
        for (int i = 1; i <= n; ++i) {
            if (i == anchor2) continue;
            char t = classify_pair(anchor2, i);
            if (t == 'F') {
                partner = i; // HM
                break;
            }
        }
        ans1 = anchor2;
        ans2 = partner;
    } else {
        // Should never happen, fallback
        ans1 = 1;
        ans2 = 2;
    }

    cout << "1 " << ans1 << " " << ans2 << endl;
    cout.flush();
    return 0;
}