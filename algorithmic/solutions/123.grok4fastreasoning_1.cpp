#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> flex, forced;
    for (int i = 1; i <= n; i++) flex.push_back(i);
    while (flex.size() + forced.size() > 2) {
        vector<int> s_list;
        vector<char> inS(n + 1, 0);
        size_t nf = forced.size();
        size_t num_f_in = nf / 2;
        for (size_t i = 0; i < num_f_in; i++) {
            int x = forced[i];
            s_list.push_back(x);
            inS[x] = 1;
        }
        size_t nx = flex.size();
        size_t num_x_in = nx / 2;
        for (size_t i = 0; i < num_x_in; i++) {
            int x = flex[i];
            s_list.push_back(x);
            inS[x] = 1;
        }
        cout << "? " << s_list.size();
        for (int v : s_list) {
            cout << " " << v;
        }
        cout << endl;
        cout.flush();
        string rep;
        cin >> rep;
        int R = (rep == "YES" ? 1 : 0);
        vector<int> new_flex, new_forced;
        for (int x : flex) {
            int T = inS[x];
            bool lied = (R != T);
            if (lied) {
                new_forced.push_back(x);
            } else {
                new_flex.push_back(x);
            }
        }
        for (int x : forced) {
            int T = inS[x];
            if (R == T) {
                new_flex.push_back(x);
            }
        }
        flex = std::move(new_flex);
        forced = std::move(new_forced);
    }
    vector<int> candidates;
    candidates.reserve(flex.size() + forced.size());
    candidates.insert(candidates.end(), flex.begin(), flex.end());
    candidates.insert(candidates.end(), forced.begin(), forced.end());
    size_t numc = candidates.size();
    if (numc == 0) {
        return 1;
    } else if (numc == 1) {
        cout << "! " << candidates[0] << endl;
        cout.flush();
        string res;
        cin >> res;
    } else {
        int y1 = candidates[0];
        int y2 = candidates[1];
        cout << "! " << y1 << endl;
        cout.flush();
        string res;
        cin >> res;
        if (res == ":)") {
        } else {
            cout << "! " << y2 << endl;
            cout.flush();
            cin >> res;
        }
    }
    return 0;
}