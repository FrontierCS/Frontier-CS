#include <bits/stdc++.h>
using namespace std;

int query_count = 0;

int query(const vector<int>& s) {
    query_count++;
    cout << "Query " << s.size();
    for (int x : s) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer(int a, int b) {
    cout << "Answer " << a << " " << b << endl;
}

int main() {
    int N;
    cin >> N;
    int total = 2 * N;
    
    // Determine gender partition using chameleon 1 as reference
    vector<int> same, opp;
    for (int i = 2; i <= total; i++) {
        vector<int> q = {1, i};
        int res = query(q);
        if (res == 2) same.push_back(i);
        else opp.push_back(i);
    }
    // Include chameleon 1 in same gender set
    same.push_back(1);
    // Now same and opp each have size N.
    // We assume same are X, opp are Y.
    vector<int> X = same;
    vector<int> Y = opp;
    // Shuffle to avoid worst-case
    random_shuffle(X.begin(), X.end());
    sort(Y.begin(), Y.end());
    
    vector<bool> used_y(N, false);
    vector<int> partner_of_x(N, -1);
    
    for (int idx = 0; idx < N; idx++) {
        int x = X[idx];
        // Build list of available Y indices
        vector<int> avail;
        for (int i = 0; i < N; i++) if (!used_y[i]) avail.push_back(i);
        int low = 0, high = (int)avail.size() - 1;
        while (low < high) {
            int mid = (low + high) / 2;
            // Build B from avail[low..mid] (actual Y IDs)
            vector<int> B;
            for (int i = low; i <= mid; i++) B.push_back(Y[avail[i]]);
            int size1 = B.size();
            // Build complement from remaining available Y
            vector<int> Bcomp;
            for (int i = 0; i < (int)avail.size(); i++) {
                if (i < low || i > mid) Bcomp.push_back(Y[avail[i]]);
            }
            int size2 = Bcomp.size();
            
            vector<int> S1 = B;
            S1.push_back(x);
            int r1 = query(S1);
            vector<int> S2 = Bcomp;
            S2.push_back(x);
            int r2 = query(S2);
            
            int d1 = r1 - size1;
            int d2 = r2 - size2;
            
            if (d1 == 0 && d2 == 1) {
                // partner is in B
                high = mid;
            } else if (d1 == 1 && d2 == 0) {
                // partner is not in B
                low = mid + 1;
            } else {
                // ambiguous (0,0) – choose left side
                high = mid;
            }
        }
        // low == high, unique candidate
        int y_idx = avail[low];
        partner_of_x[idx] = y_idx;
        used_y[y_idx] = true;
    }
    
    // Output answers
    for (int i = 0; i < N; i++) {
        answer(X[i], Y[partner_of_x[i]]);
    }
    
    return 0;
}