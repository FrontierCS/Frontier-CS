#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> F;

int getF(int l, int r) {
    if (l >= r) return 0;
    int &res = F[l][r];
    if (res != -1) return res;
    cout << "0 " << l << " " << r << endl;
    cout.flush();
    if (!(cin >> res)) exit(0);
    res &= 1;
    return res;
}

int pairGreater(int l, int r) { // assumes l < r, returns [p_l > p_r]
    int a = getF(l, r);
    int b = getF(l + 1, r);
    int c = getF(l, r - 1);
    int d = 0;
    if (l + 1 < r) d = getF(l + 1, r - 1);
    return a ^ b ^ c ^ d;
}

bool isLessIndex(int i, int j) { // returns true if p_i < p_j
    if (i == j) return false;
    if (i < j) {
        int g = pairGreater(i, j); // [p_i > p_j]
        return !g;
    } else {
        int g = pairGreater(j, i); // [p_j > p_i]
        return g;                  // p_i < p_j <=> p_j > p_i
    }
}

void merge_sort(vector<int> &a, int l, int r) {
    if (r - l <= 1) return;
    int m = (l + r) / 2;
    merge_sort(a, l, m);
    merge_sort(a, m, r);
    vector<int> tmp;
    tmp.reserve(r - l);
    int i = l, j = m;
    while (i < m && j < r) {
        if (isLessIndex(a[i], a[j])) {
            tmp.push_back(a[i++]);
        } else {
            tmp.push_back(a[j++]);
        }
    }
    while (i < m) tmp.push_back(a[i++]);
    while (j < r) tmp.push_back(a[j++]);
    for (int k = 0; k < r - l; ++k) a[l + k] = tmp[k];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    F.assign(n + 2, vector<int>(n + 2, -1));

    vector<int> idx(n);
    for (int i = 0; i < n; ++i) idx[i] = i + 1;

    merge_sort(idx, 0, n);

    vector<int> p(n + 1);
    for (int k = 0; k < n; ++k) {
        p[idx[k]] = k + 1;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}