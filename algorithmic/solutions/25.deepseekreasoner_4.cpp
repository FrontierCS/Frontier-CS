#include <bits/stdc++.h>
using namespace std;

int n;
int queries = 0;

int query(const string& s) {
    cout << "? " << s << endl;
    int ans;
    cin >> ans;
    if (ans == -1) exit(0); // in case of error
    ++queries;
    return ans;
}

// convert bitmask (vector<bool> or bitset) to string
string mask_to_string(const vector<bool>& m) {
    string s(n, '0');
    for (int i = 0; i < n; ++i)
        if (m[i])
            s[i] = '1';
    return s;
}

// find a vertex in U that is adjacent to C using binary search
// C is fixed, U is a list of vertices
int find_neighbor(const vector<bool>& C, const vector<int>& U) {
    if (U.size() == 1) return U[0];
    // split U into two halves
    int mid = U.size() / 2;
    vector<int> L(U.begin(), U.begin() + mid);
    vector<int> R(U.begin() + mid, U.end());
    
    // query C union L
    vector<bool> tmp = C;
    for (int v : L) tmp[v] = true;
    int qCL = query(mask_to_string(tmp));
    
    // query C
    int qC = query(mask_to_string(C));
    
    if (qCL < qC) {
        return find_neighbor(C, L);
    } else {
        return find_neighbor(C, R);
    }
}

void solve() {
    cin >> n;
    queries = 0;
    
    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }
    
    vector<bool> C(n, false);
    C[0] = true; // start from vertex 1 (index 0)
    vector<int> U;
    for (int i = 1; i < n; ++i) U.push_back(i);
    
    while (!U.empty()) {
        // query U (complement of C)
        vector<bool> maskU(n, false);
        for (int v : U) maskU[v] = true;
        int qU = query(mask_to_string(maskU));
        if (qU == 0) {
            cout << "! 0" << endl;
            return;
        }
        
        // find a vertex v in U adjacent to C
        int v = find_neighbor(C, U);
        // add v to C
        C[v] = true;
        // remove v from U
        U.erase(find(U.begin(), U.end(), v));
    }
    
    cout << "! 1" << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    
    return 0;
}