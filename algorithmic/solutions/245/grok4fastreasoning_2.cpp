#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        int num_pairs = n / 2;
        bool odd = (n % 2 == 1);
        if (odd) num_pairs = (n - 1) / 2;
        vector<int> lefts(num_pairs), rights(num_pairs);
        vector<int> ans1(num_pairs), ans2(num_pairs);
        bool has_oneone = false;
        int oneone_k = -1;
        bool has_asym = false;
        int asym_k = -1;
        for (int k = 0; k < num_pairs; k++) {
            int left = 2 * k + 1;
            int right = left + 1;
            lefts[k] = left;
            rights[k] = right;
            cout << "? " << left << " " << right << endl;
            fflush(stdout);
            int a1;
            cin >> a1;
            if (a1 == -1) return 0;
            ans1[k] = a1;
            cout << "? " << right << " " << left << endl;
            fflush(stdout);
            int a2;
            cin >> a2;
            if (a2 == -1) return 0;
            ans2[k] = a2;
            if (a1 == 1 && a2 == 1) {
                has_oneone = true;
                oneone_k = k;
            }
            if (a1 != a2) {
                has_asym = true;
                asym_k = k;
            }
        }
        int impostor;
        if (!has_asym) {
            impostor = n;
        } else {
            int x = lefts[asym_k];
            int y = rights[asym_k];
            int a = ans1[asym_k]; // ?x y
            int b = ans2[asym_k]; // ?y x
            bool swapped = false;
            if (a == 0 && b == 1) {
                swap(x, y);
                swapped = true;
                // now ?x y should be 1, ?y x =0, but since swapped, we don't need the values anymore
            }
            // now assume ?x y=1, ?y x=0
            int zz;
            if (has_oneone) {
                zz = lefts[oneone_k];
            } else {
                zz = 1;
                if (zz == x || zz == y) zz = 2;
                if (zz == x || zz == y) zz = 3;
            }
            cout << "? " << zz << " " << x << endl;
            fflush(stdout);
            int c1;
            cin >> c1;
            if (c1 == -1) return 0;
            cout << "? " << zz << " " << y << endl;
            fflush(stdout);
            int c2;
            cin >> c2;
            if (c2 == -1) return 0;
            if ((c1 == 1 && c2 == 1) || (c1 == 0 && c2 == 0)) {
                impostor = y;
            } else {
                impostor = x;
            }
        }
        cout << "! " << impostor << endl;
        fflush(stdout);
    }
    return 0;
}