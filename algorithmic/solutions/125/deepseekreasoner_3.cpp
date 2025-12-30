#include <bits/stdc++.h>
using namespace std;

int N;
int current_r;

int toggle(int x) {
    cout << "? " << x << endl;
    int r;
    cin >> r;
    current_r = r;
    return r;
}

void output_pair(int a, int b) {
    cout << "! " << a << " " << b << endl;
}

void solve_cross(vector<int>& L, vector<int>& R);

void solve(vector<int>& indices) {
    int m = indices.size();
    if (m == 2) {
        output_pair(indices[0], indices[1]);
        return;
    }
    if (m == 0) return;
    int mid = m / 2;
    vector<int> A(indices.begin(), indices.begin() + mid);
    vector<int> B(indices.begin() + mid, indices.end());
    
    // Insert A
    for (int x : A) toggle(x);
    int rA = current_r;
    
    vector<int> A_internal, A_external;
    for (int x : A) {
        toggle(x); // remove x
        if (current_r == rA) {
            A_internal.push_back(x);
        } else {
            A_external.push_back(x);
        }
        toggle(x); // insert back
    }
    
    vector<int> B_internal, B_external;
    for (int y : B) {
        toggle(y); // insert y
        if (current_r == rA) {
            B_external.push_back(y);
        } else {
            B_internal.push_back(y);
        }
        toggle(y); // remove y
    }
    
    // Remove A
    for (int x : A) toggle(x);
    
    solve(A_internal);
    solve(B_internal);
    if (!A_external.empty()) {
        solve_cross(A_external, B_external);
    }
}

void solve_cross(vector<int>& L, vector<int>& R) {
    int k = L.size();
    if (k == 1) {
        output_pair(L[0], R[0]);
        return;
    }
    int mid = k / 2;
    vector<int> L1(L.begin(), L.begin() + mid);
    vector<int> L2(L.begin() + mid, L.end());
    
    // Insert L1
    for (int x : L1) toggle(x);
    int rL1 = current_r;
    
    vector<int> R1, R2;
    for (int y : R) {
        toggle(y);
        if (current_r == rL1) {
            R1.push_back(y);
        } else {
            R2.push_back(y);
        }
        toggle(y);
    }
    
    // Remove L1
    for (int x : L1) toggle(x);
    
    solve_cross(L1, R1);
    solve_cross(L2, R2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> N;
    current_r = 0;
    vector<int> all(2 * N);
    iota(all.begin(), all.end(), 1);
    solve(all);
    
    return 0;
}