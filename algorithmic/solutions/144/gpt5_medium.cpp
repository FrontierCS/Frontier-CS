#include <bits/stdc++.h>
using namespace std;

pair<int,int> query_excluding(int n, int ex1, int ex2) {
    vector<int> S;
    S.reserve(n-2);
    for (int i = 1; i <= n; ++i) {
        if (i == ex1 || i == ex2) continue;
        S.push_back(i);
    }
    cout << 0 << " " << (int)S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();

    int a, b;
    if (!(cin >> a >> b)) {
        // In case of interaction failure, exit.
        exit(0);
    }
    return {a, b};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int L = n / 2;
    int R = L + 1;

    int j = 1;
    vector<pair<int,int>> res(n+1, {-1,-1});

    for (int i = 1; i <= n; ++i) {
        if (i == j) continue;
        auto pr = query_excluding(n, i, j);
        int a = pr.first, b = pr.second;
        // Check for special case indicating i and j are the medians' indices
        if (a == L-1 && b == R+1) {
            cout << 1 << " " << i << " " << j << endl;
            cout.flush();
            return 0;
        }
        res[i] = pr;
    }

    // Analyze results to find indices
    int idxL = -1, idxR = -1;
    vector<int> midBoth; // (L-1, R)
    for (int i = 1; i <= n; ++i) {
        if (i == j) continue;
        auto [a,b] = res[i];
        if (a == R && b == R+1) idxL = i;       // j is low: i == L
        if (a == L && b == R+1) idxR = i;       // j is low: i == R
        if (a == L-1 && b == R) midBoth.push_back(i); // j is high: i in {L, R}
    }

    if (idxL != -1 && idxR != -1) {
        cout << 1 << " " << idxL << " " << idxR << endl;
        cout.flush();
        return 0;
    }

    if ((int)midBoth.size() == 2) {
        cout << 1 << " " << midBoth[0] << " " << midBoth[1] << endl;
        cout.flush();
        return 0;
    }

    // Fallback (should not happen based on analysis)
    // Try another j just in case; but we must stay within query limit.
    // Choose j=2 if j==1.
    int j2 = (j == 1 ? 2 : 1);
    res.assign(n+1, {-1,-1});
    for (int i = 1; i <= n; ++i) {
        if (i == j2) continue;
        auto pr = query_excluding(n, i, j2);
        int a = pr.first, b = pr.second;
        if (a == L-1 && b == R+1) {
            cout << 1 << " " << i << " " << j2 << endl;
            cout.flush();
            return 0;
        }
        res[i] = pr;
    }
    idxL = idxR = -1;
    midBoth.clear();
    for (int i = 1; i <= n; ++i) {
        if (i == j2) continue;
        auto [a,b] = res[i];
        if (a == R && b == R+1) idxL = i;
        if (a == L && b == R+1) idxR = i;
        if (a == L-1 && b == R) midBoth.push_back(i);
    }
    if (idxL != -1 && idxR != -1) {
        cout << 1 << " " << idxL << " " << idxR << endl;
        cout.flush();
        return 0;
    }
    if ((int)midBoth.size() == 2) {
        cout << 1 << " " << midBoth[0] << " " << midBoth[1] << endl;
        cout.flush();
        return 0;
    }

    // As a last resort, output two arbitrary indices to terminate.
    cout << 1 << " " << 1 << " " << 2 << endl;
    cout.flush();
    return 0;
}