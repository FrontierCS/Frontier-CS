#include <bits/stdc++.h>
using namespace std;

const int INF = 1e9;

// 2D Sparse Table for range minimum query
template<typename T>
struct SparseTable2D {
    vector<vector<vector<vector<T>>>> st;
    vector<int> log;
    int n, m;
    
    SparseTable2D(const vector<vector<T>>& a) {
        n = a.size();
        m = a[0].size();
        int logn = 0, logm = 0;
        while ((1 << logn) <= n) logn++;
        while ((1 << logm) <= m) logm++;
        st.assign(logn, vector<vector<vector<T>>>(logm, vector<vector<T>>(n, vector<T>(m))));
        
        // Base level
        for (int i = 0; i < n; i++)
            for (int j = 0; j < m; j++)
                st[0][0][i][j] = a[i][j];
        
        // Preprocess rows
        for (int p = 1; p < logn; p++)
            for (int i = 0; i + (1 << p) <= n; i++)
                for (int j = 0; j < m; j++)
                    st[p][0][i][j] = min(st[p-1][0][i][j], st[p-1][0][i+(