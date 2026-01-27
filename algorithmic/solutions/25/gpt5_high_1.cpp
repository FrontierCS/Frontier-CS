#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        vector<char> done(n, 0);
        int components = 0;

        auto query_with_set = [&](const vector<char>& inS)->int{
            string s;
            s.reserve(n + 3);
            s.assign(n, '0');
            for (int i = 0; i < n; ++i) if (inS[i]) s[i] = '1';
            cout << "? " << s << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) exit(0);
            return ans;
        };

        while (true) {
            int v = -1;
            for (int i = 0; i < n; ++i) if (!done[i]) { v = i; break; }
            if (v == -1) break; // all done

            components++;

            vector<char> present(n, 0); // CurrentY membership
            vector<int> Y0;
            for (int i = 0; i < n; ++i) {
                if (!done[i] && i != v) {
                    present[i] = 1;
                    Y0.push_back(i);
                }
            }

            // Build a function to test if we can remove a subset Z from CurrentY
            function<bool(const vector<int>&)> can_remove = [&](const vector<int>& Z)->bool{
                vector<char> inS(n, 0);
                for (int i = 0; i < n; ++i) if (done[i]) inS[i] = 1;
                inS[v] = 1;
                for (int i = 0; i < n; ++i) if (present[i]) inS[i] = 1;
                for (int idx : Z) inS[idx] = 0;
                int ans = query_with_set(inS);
                return ans == 0;
            };

            function<void(const vector<int>&)> remove_rec = [&](const vector<int>& Z){
                if (Z.empty()) return;
                if (can_remove(Z)) {
                    for (int x : Z) present[x] = 0;
                    return;
                }
                if (Z.size() == 1) {
                    // This element is required; keep it
                    return;
                }
                int mid = (int)Z.size() / 2;
                vector<int> L(Z.begin(), Z.begin() + mid);
                vector<int> R(Z.begin() + mid, Z.end());
                remove_rec(L);
                remove_rec(R);
            };

            remove_rec(Y0);

            // Mark component vertices as done
            done[v] = 1;
            for (int i = 0; i < n; ++i) if (present[i]) done[i] = 1;
        }

        int connected = (components == 1) ? 1 : 0;
        cout << "! " << connected << endl;
        cout.flush();
    }

    return 0;
}