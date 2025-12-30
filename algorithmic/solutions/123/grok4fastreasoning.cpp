#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    cin >> n;
    vector<int> set_zero;
    for (int i = 1; i <= n; ++i) {
        set_zero.push_back(i);
    }
    vector<int> set_one;
    int qused = 0;
    while (set_zero.size() + set_one.size() > 2) {
        size_t sz1 = set_one.size();
        size_t z = sz1 / 2;
        vector<int> Z(set_one.begin(), set_one.begin() + z);
        size_t sz0 = set_zero.size();
        size_t h = sz0 / 2;
        vector<int> D(set_zero.begin(), set_zero.begin() + h);
        vector<int> Sin;
        Sin.reserve(z + h);
        Sin.insert(Sin.end(), D.begin(), D.end());
        Sin.insert(Sin.end(), Z.begin(), Z.end());
        cout << "? " << Sin.size();
        for (int y : Sin) {
            cout << " " << y;
        }
        cout << "\n";
        cout.flush();
        string A;
        cin >> A;
        ++qused;
        vector<char> is_in(n + 1, 0);
        for (int y : Sin) {
            is_in[y] = 1;
        }
        vector<int> new_zero;
        vector<int> new_one;
        bool ry = (A == "YES");
        for (int x : set_zero) {
            bool ins = is_in[x];
            bool ty = ins;
            if (ty == ry) {
                new_zero.push_back(x);
            } else {
                new_one.push_back(x);
            }
        }
        for (int x : set_one) {
            bool ins = is_in[x];
            bool ty = ins;
            if (ty == ry) {
                new_zero.push_back(x);
            }
        }
        set_zero = move(new_zero);
        set_one = move(new_one);
    }
    set<int> cands;
    for (int x : set_zero) cands.insert(x);
    for (int x : set_one) cands.insert(x);
    vector<int> candidates(cands.begin(), cands.end());
    for (int g : candidates) {
        cout << "! " << g << "\n";
        cout.flush();
        string res;
        cin >> res;
        if (res == ":)") {
            return 0;
        }
    }
    return 0;
}