#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    for(int test = 0; test < t; test++) {
        int n;
        cin >> n;
        if(n == -1) return 0;
        int m = 2 * n - 1;
        int low = 1, high = m;
        int max_k = 5;
        while(high - low + 1 > max_k) {
            int mid = low + (high - low) / 2;
            int size_s = mid - low + 1;
            vector<int> appear_s(n + 1, 0);
            for(int x = 1; x <= n; x++) {
                cout << "? " << x << " " << size_s;
                for(int p = low; p <= mid; p++) cout << " " << p;
                cout << endl;
                cout.flush();
                int res;
                cin >> res;
                if(res == -1) return 0;
                appear_s[x] = res;
            }
            vector<int> pos_comp;
            for(int p = 1; p < low; p++) pos_comp.push_back(p);
            for(int p = mid + 1; p <= m; p++) pos_comp.push_back(p);
            int size_comp = pos_comp.size();
            vector<int> appear_comp(n + 1, 0);
            for(int x = 1; x <= n; x++) {
                cout << "? " << x << " " << size_comp;
                for(int p : pos_comp) cout << " " << p;
                cout << endl;
                cout.flush();
                int res;
                cin >> res;
                if(res == -1) return 0;
                appear_comp[x] = res;
            }
            int ss = 0;
            for(int x = 1; x <= n; x++) if(appear_s[x] && appear_comp[x]) ss++;
            int delta = (size_s - ss) % 2;
            if(delta < 0) delta += 2;
            if(delta == 1) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        // now small
        int k = high - low + 1;
        vector<int> small_pos(k);
        for(int i = 0; i < k; i++) small_pos[i] = low + i;
        vector<int> appear_small(n + 1, 0);
        for(int x = 1; x <= n; x++) {
            cout << "? " << x << " " << k;
            for(int p : small_pos) cout << " " << p;
            cout << endl;
            cout.flush();
            int res;
            cin >> res;
            if(res == -1) return 0;
            appear_small[x] = res;
        }
        vector<int> cand_x;
        for(int x = 1; x <= n; x++) if(appear_small[x]) cand_x.push_back(x);
        int nc = cand_x.size();
        vector<int> count_small(nc, 0);
        for(int i = 0; i < nc; i++) {
            int x = cand_x[i];
            int cnt = 0;
            for(int j = 0; j < k; j++) {
                int pos = small_pos[j];
                cout << "? " << x << " 1 " << pos << endl;
                cout.flush();
                int res;
                cin >> res;
                if(res == -1) return 0;
                if(res == 1) cnt++;
            }
            count_small[i] = cnt;
        }
        // comp pos
        vector<int> comp_pos;
        for(int p = 1; p <= m; p++) {
            bool ins = false;
            for(int sp : small_pos) if(sp == p) {ins = true; break;}
            if(!ins) comp_pos.push_back(p);
        }
        int size_csmall = comp_pos.size();
        int y = -1;
        for(int i = 0; i < nc; i++) {
            int x = cand_x[i];
            if(count_small[i] == 1) {
                cout << "? " << x << " " << size_csmall;
                for(int p : comp_pos) cout << " " << p;
                cout << endl;
                cout.flush();
                int res;
                cin >> res;
                if(res == -1) return 0;
                if(res == 0) {
                    y = x;
                    break;
                }
            }
        }
        cout << "! " << y << endl;
        cout.flush();
    }
    return 0;
}