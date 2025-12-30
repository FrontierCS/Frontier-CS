#include <bits/stdc++.h>
using namespace std;

vector<pair<int, int>> ask(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    cout.flush();
    int r;
    cin >> r;
    vector<pair<int, int>> res;
    for (int i = 0; i < r; ++i) {
        int a, b;
        cin >> a >> b;
        if (a > b) swap(a, b);
        res.emplace_back(a, b);
    }
    return res;
}

bool contains(const vector<pair<int, int>> &v, pair<int, int> p) {
    return find(v.begin(), v.end(), p) != v.end();
}

bool compare(int A, int B, int C) {
    if (B == C) return false;
    auto res = ask(A, B, C);
    bool ab = contains(res, {A, B});
    bool ac = contains(res, {A, C});
    if (ab && !ac) return true;
    if (ac && !ab) return false;
    return false;
}

bool isOnBSide(int B, int C, int X) {
    auto res = ask(B, C, X);
    bool bx = contains(res, {B, X});
    bool cx = contains(res, {C, X});
    if (bx && !cx) return true;
    if (cx && !bx) return false;
    return true;
}

int main() {
    int k, n;
    cin >> k >> n;

    int A = 0;
    vector<int> points;
    for (int i = 1; i < n; ++i) points.push_back(i);

    stable_sort(points.begin(), points.end(), [&](int B, int C) {
        return compare(A, B, C);
    });

    int B = points[0], C = points[1];
    vector<int> listB = {B}, listC = {C};

    for (size_t i = 2; i < points.size(); ++i) {
        int X = points[i];
        if (isOnBSide(B, C, X))
            listB.push_back(X);
        else
            listC.push_back(X);
    }

    cout << "! " << A;
    for (int x : listB) cout << " " << x;
    for (auto it = listC.rbegin(); it != listC.rend(); ++it)
        cout << " " << *it;
    cout << endl;
    cout.flush();

    return 0;
}