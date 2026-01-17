#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>

using namespace std;

int N, M;
vector<pair<int, int>> edges;

int ask(const vector<int>& dir) {
    cout << 0;
    for (int d : dir) {
        cout << " " << d;
    }
    cout << endl;
    int response;
    cin >> response;
    if (response == -1) exit(0);
    return response;
}

// orient edges from S to V\S, returns 0 if A in V\S, B in S
int query_from_S(const vector<bool>& inS) {
    vector<int> dir(M);
    for (int i = 0; i < M; ++i) {
        bool u_inS = inS[edges[i].first];
        bool v_inS = inS[edges[i].second];
        if (u_inS && !v_inS) {
            dir[i] = 0; // U_i -> V_i
        } else if (!u_inS && v_inS) {
            dir[i] = 1; // V_i -> U_i
        } else {
            dir[i] = 0; // arbitrary
        }
    }
    return ask(dir);
}

// orient edges from V\S to S, returns 0 if A in S, B in V\S
int query_to_S(const vector<bool>& inS) {
    vector<int> dir(M);
    for (int i = 0; i < M; ++i) {
        bool u_inS = inS[edges[i].first];
        bool v_inS = inS[edges[i].second];
        if (u_inS && !v_inS) {
            dir[i] = 1; // V_i -> U_i
        } else if (!u_inS && v_inS) {
            dir[i] = 0; // U_i -> V_i
        } else {
            dir[i] = 0; // arbitrary
        }
    }
    return ask(dir);
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;
    edges.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }

    int A_val = 0;
    int X = 0;
    vector<int> same_bits_indices;
    int log_N = 0;
    while ((1 << log_N) < N) {
        log_N++;
    }

    for (int k = 0; k < log_N; ++k) {
        vector<bool> inS(N, false);
        for (int i = 0; i < N; ++i) {
            if ((i >> k) & 1) {
                inS[i] = true;
            }
        }

        int res_to_S = query_to_S(inS);
        if (res_to_S == 0) { // A in S, B not in S => bit_k(A)=1, bit_k(B)=0
            A_val |= (1 << k);
            X |= (1 << k);
            continue;
        }

        int res_from_S = query_from_S(inS);
        if (res_from_S == 0) { // A not in S, B in S => bit_k(A)=0, bit_k(B)=1
            X |= (1 << k);
            continue;
        }
        
        same_bits_indices.push_back(k); // bit_k(A) == bit_k(B)
    }
    
    int B_val_known_part = A_val ^ X;

    int diff_mask = 0;
    vector<bool> is_same(log_N + 1, false);
    for(int k : same_bits_indices) is_same[k] = true;
    for(int i=0; i<log_N; ++i) {
        if(!is_same[i]) diff_mask |= (1 << i);
    }

    int A_p = A_val & diff_mask;
    int B_p = B_val_known_part & diff_mask;

    for (int k : same_bits_indices) {
        vector<bool> inS(N, false);

        for (int i = 0; i < N; ++i) {
            // is i a candidate for A with bit_k = 0?
            if (((i & diff_mask) == A_p) && !((i >> k) & 1)) {
                inS[i] = true;
            }
            // is i a candidate for B with bit_k = 1?
            if (((i & diff_mask) == B_p) && ((i >> k) & 1)) {
                inS[i] = true;
            }
        }
        
        // if bit_k(A)=1, then A is not in S, B is in S.
        int res = query_from_S(inS);
        if (res == 0) {
            A_val |= (1 << k);
        }
    }

    int B_val = A_val ^ X;

    cout << 1 << " " << A_val << " " << B_val << endl;

    return 0;
}