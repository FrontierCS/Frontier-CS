#include <bits/stdc++.h>
using namespace std;

int n;

// Query function: send binary string s, return answer
int query(const string& s) {
    cout << "? " << s << endl;
    int res;
    cin >> res;
    return res;
}

// Convert bitset to string
string to_string(const vector<bool>& bs) {
    string s(n, '0');
    for (int i = 0; i < n; i++) {
        if (bs[i]) s[i] = '1';
    }
    return s;
}

// Find a non-empty subset T of U such that f(C ∪ T) < fC.
// U is given as a list of vertex indices (all not in C).
// Returns the list of vertices in T.
vector<int> find_subset(const vector<bool>& C, int fC, const vector<int>& U) {
    if (U.empty()) return {};
    if (U.size() == 1) {
        int v = U[0];
        vector<bool> Cv = C;
        Cv[v] = true;
        int fCv = query(to_string(Cv));
        if (fCv < fC) {
            return {v};
        } else {
            return {};
        }
    }
    // Split U into two halves
    int m = U.size() / 2;
    vector<int> L(U.begin(), U.begin() + m);
    vector<int> R(U.begin() + m, U.end());
    
    // Query f(C ∪ L) and f(C ∪ R)
    vector<bool> CL = C, CR = C;
    for (int v : L) CL[v] = true;
    for (int v : R) CR[v] = true;
    int fCL = query(to_string(CL));
    int fCR = query(to_string(CR));
    
    if (fCL < fC) {
        return find_subset(C, fC, L);
    } else if (fCR < fC) {
        return find_subset(C, fC, R);
    } else {
        // Neither half reduces f individually.
        // Set C' = C ∪ L, then find subset of R that reduces f(C')
        vector<bool> Cprime = CL; // already set
        int fCprime = fCL;
        vector<int> T_R = find_subset(Cprime, fCprime, R);
        if (T_R.empty()) {
            return {}; // should not happen if graph is connected
        }
        // Return L ∪ T_R
        vector<int> res = L;
        res.insert(res.end(), T_R.begin(), T_R.end());
        return res;
    }
}

void solve() {
    cin >> n;
    vector<int> degree(n);
    bool isolated = false;
    // Query all singletons
    for (int i = 0; i < n; i++) {
        string s(n, '0');
        s[i] = '1';
        degree[i] = query(s);
        if (n > 1 && degree[i] == 0) {
            isolated = true;
        }
    }
    if (isolated) {
        cout << "! 0" << endl;
        return;
    }
    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }
    
    vector<bool> vis(n, false);
    vis[0] = true;
    int visited = 1;
    vector<bool> C(n, false);
    C[0] = true;
    
    while (visited < n) {
        // Query f(C)
        int fC = query(to_string(C));
        if (fC == 0) {
            // No edge from current component to outside -> disconnected
            cout << "! 0" << endl;
            return;
        }
        // Build list of unvisited vertices
        vector<int> U;
        for (int i = 0; i < n; i++) {
            if (!vis[i]) U.push_back(i);
        }
        // Find a subset T of U that reduces f(C)
        vector<int> T = find_subset(C, fC, U);
        if (T.empty()) {
            // This should not happen if graph is connected, but to be safe:
            cout << "! 0" << endl;
            return;
        }
        // Add all vertices in T to C
        for (int v : T) {
            if (!vis[v]) {
                vis[v] = true;
                C[v] = true;
                visited++;
            }
        }
    }
    // All vertices visited -> connected
    cout << "! 1" << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    cin >> T;
    while (