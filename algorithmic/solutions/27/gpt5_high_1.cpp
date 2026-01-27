#include <bits/stdc++.h>
using namespace std;

static bool isPrime(int x){
    if(x < 2) return false;
    if(x % 2 == 0) return x == 2;
    for(int i = 3; 1LL*i*i <= x; i += 2){
        if(x % i == 0) return false;
    }
    return true;
}

static int largestPrimeLE(int x){
    for(int p = x; p >= 2; --p){
        if(isPrime(p)) return p;
    }
    return 0;
}

static vector<pair<int,int>> baseline(int n, int m){
    vector<pair<int,int>> res;
    res.reserve(n + m - 1);
    // Full row 1
    for(int c = 1; c <= m; ++c) res.emplace_back(1, c);
    // Full column 1 (skip (1,1))
    for(int r = 2; r <= n; ++r) res.emplace_back(r, 1);
    return res;
}

static vector<pair<int,int>> row_affine(int n, int m){
    int s = (int)floor(sqrt((long double)m));
    int p = largestPrimeLE(s);
    if(p < 2) return {};
    int L = min(n, p*p + p);

    vector<pair<int,int>> res;
    res.reserve((size_t)L * (p + 2) + (size_t)(m - p*p)); // rough reservation

    vector<int> slopeOfRow(L+1, -1);
    vector<vector<int>> rowsBySlope(p+1);

    int row = 1;
    // Non-vertical lines: y = a*x + b
    for(int a = 0; a < p && row <= L; ++a){
        for(int b = 0; b < p && row <= L; ++b){
            slopeOfRow[row] = a;
            rowsBySlope[a].push_back(row);
            for(int x = 0; x < p; ++x){
                int y = (a * x + b) % p;
                int col = x * p + y + 1;
                res.emplace_back(row, col);
            }
            ++row;
        }
    }
    // Vertical lines: x = const
    for(int x = 0; x < p && row <= L; ++x){
        slopeOfRow[row] = p; // vertical category
        rowsBySlope[p].push_back(row);
        for(int y = 0; y < p; ++y){
            int col = x * p + y + 1;
            res.emplace_back(row, col);
        }
        ++row;
    }

    // Leftover rows: initially give them column 1
    for(int r = L + 1; r <= n; ++r){
        res.emplace_back(r, 1);
    }

    // Add "points at infinity" columns for slope categories to boost
    int availableCols = m - p * p;
    if(availableCols > 0){
        int maxInf = min(p + 1, availableCols);
        vector<pair<int,int>> cntSlope;
        cntSlope.reserve(p+1);
        for(int sidx = 0; sidx <= p; ++sidx){
            int cnt = (int)rowsBySlope[sidx].size();
            if(cnt > 0) cntSlope.emplace_back(cnt, sidx);
        }
        sort(cntSlope.begin(), cntSlope.end(), [&](const pair<int,int>& A, const pair<int,int>& B){
            if(A.first != B.first) return A.first > B.first;
            return A.second < B.second;
        });
        int useInf = min(maxInf, (int)cntSlope.size());
        int infUsed = 0;
        for(int i = 0; i < useInf; ++i){
            int sidx = cntSlope[i].second;
            int col = p * p + (infUsed + 1);
            for(int r : rowsBySlope[sidx]){
                res.emplace_back(r, col);
            }
            ++infUsed;
        }
        availableCols -= infUsed;

        // Use remaining columns as unique columns, assign to leftover rows first, then to row 1
        int colNext = p * p + (min(maxInf, (int)cntSlope.size())) + 1;
        int rem = availableCols;
        int leftoverRows = n - L;
        int giveToLeftovers = min(rem, leftoverRows);
        for(int i = 0; i < giveToLeftovers; ++i){
            int r = L + 1 + i;
            res.emplace_back(r, colNext++);
        }
        rem -= giveToLeftovers;
        if(rem > 0){
            int r = 1; // any single row, unique columns won't create rectangles
            for(int i = 0; i < rem; ++i){
                res.emplace_back(r, colNext++);
            }
        }
    }

    return res;
}

static vector<pair<int,int>> col_affine(int n, int m){
    int s = (int)floor(sqrt((long double)n));
    int q = largestPrimeLE(s);
    if(q < 2) return {};
    int M = min(m, q*q + q);

    vector<pair<int,int>> res;
    res.reserve((size_t)M * (q + 1) + (m - M));

    int col = 1;
    // Non-vertical lines: y = a*x + b
    for(int a = 0; a < q && col <= M; ++a){
        for(int b = 0; b < q && col <= M; ++b){
            for(int x = 0; x < q; ++x){
                int y = (a * x + b) % q;
                int r = x * q + y + 1;
                res.emplace_back(r, col);
            }
            ++col;
        }
    }
    // Vertical lines: x = const
    for(int x = 0; x < q && col <= M; ++x){
        for(int y = 0; y < q; ++y){
            int r = x * q + y + 1;
            res.emplace_back(r, col);
        }
        ++col;
    }

    // Leftover columns: assign to row 1
    for(int c = M + 1; c <= m; ++c){
        res.emplace_back(1, c);
    }

    return res;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) return 0;

    if(n == 1 || m == 1){
        vector<pair<int,int>> res;
        res.reserve((size_t)n * m);
        for(int r = 1; r <= n; ++r){
            for(int c = 1; c <= m; ++c){
                res.emplace_back(r, c);
            }
        }
        cout << res.size() << "\n";
        for(auto &pr : res){
            cout << pr.first << " " << pr.second << "\n";
        }
        return 0;
    }

    auto A = baseline(n, m);
    auto B = row_affine(n, m);
    auto C = col_affine(n, m);

    vector<pair<int,int>> best = A;
    if(B.size() > best.size()) best = move(B);
    if(C.size() > best.size()) best = move(C);

    cout << best.size() << "\n";
    for(auto &pr : best){
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}