#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdlib>

using namespace std;

int n;
vector<int> color, parent;
vector<int> processed, list0, list1;
int eT = 0, e0 = 0, e1 = 0;

int ask_query(vector<int> s) {
    sort(s.begin(), s.end());
    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        if (i) cout << " ";
        cout << s[i];
    }
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// find one neighbor of v in set S (S non-empty, at least one edge exists)
int find_neighbor(int v, const vector<int>& S) {
    if (S.size() == 1) return S[0];
    int mid = S.size() / 2;
    vector<int> L(S.begin(), S.begin() + mid);
    vector<int> R(S.begin() + mid, S.end());
    int eL = ask_query(L);
    vector<int> Lv = L;
    Lv.push_back(v);
    int rL = ask_query(Lv);
    int degL = rL - eL;
    if (degL > 0)
        return find_neighbor(v, L);
    else
        return find_neighbor(v, R);
}

int main() {
    cin >> n;
    if (n == 1) {
        cout << "Y 1\n1\n";
        return 0;
    }

    color.assign(n + 1, -1);
    parent.assign(n + 1, -1);

    // start with vertex 1
    color[1] = 0;
    processed.push_back(1);
    list0.push_back(1);

    for (int v = 2; v <= n; ++v) {
        vector<int> T = processed;
        vector<int> Tv = T;
        Tv.push_back(v);
        int r = ask_query(Tv);
        int degT = r - eT;

        if (degT == 0) {
            // isolated from current processed vertices
            color[v] = 0;
            parent[v] = -1;
            list0.push_back(v);
        } else {
            // find one neighbor in T
            int u = find_neighbor(v, T);
            parent[v] = u;
            color[v] = 1 - color[u];

            vector<int> sameSet;
            int* eSamePtr;
            if (color[v] == 0) {
                sameSet = list0;
                eSamePtr = &e0;
            } else {
                sameSet = list1;
                eSamePtr = &e1;
            }

            if (!sameSet.empty()) {
                vector<int> sameSetV = sameSet;
                sameSetV.push_back(v);
                int r2 = ask_query(sameSetV);
                int degSame = r2 - (*eSamePtr);
                if (degSame > 0) {
                    // conflict: odd cycle found
                    int w = find_neighbor(v, sameSet);

                    // get paths from v and w to their roots
                    vector<int> path_v, path_w;
                    int a = v;
                    while (a != -1) {
                        path_v.push_back(a);
                        a = parent[a];
                    }
                    int b = w;
                    while (b != -1) {
                        path_w.push_back(b);
                        b = parent[b];
                    }
                    reverse(path_v.begin(), path_v.end());
                    reverse(path_w.begin(), path_w.end());

                    // find last common vertex (LCA)
                    int lca_idx = 0;
                    while (lca_idx < (int)path_v.size() && lca_idx < (int)path_w.size() && path_v[lca_idx] == path_w[lca_idx])
                        ++lca_idx;
                    --lca_idx; // last common index

                    // construct cycle
                    vector<int> cycle;
                    for (int i = 0; i <= lca_idx; ++i)
                        cycle.push_back(path_v[i]);
                    for (int i = path_w.size() - 1; i > lca_idx; --i)
                        cycle.push_back(path_w[i]);

                    cout << "N " << cycle.size() << endl;
                    for (size_t i = 0; i < cycle.size(); ++i) {
                        if (i) cout << " ";
                        cout << cycle[i];
                    }
                    cout << endl;
                    return 0;
                } else {
                    // update edge count inside this color class
                    *eSamePtr += degSame;
                }
            }
            // update total edges inside processed vertices
            eT += degT;
            // add v to appropriate list
            if (color[v] == 0)
                list0.push_back(v);
            else
                list1.push_back(v);
        }
        processed.push_back(v);
    }

    // graph is bipartite
    sort(list0.begin(), list0.end());
    cout << "Y " << list0.size() << endl;
    for (size_t i = 0; i < list0.size(); ++i) {
        if (i) cout << " ";
        cout << list0[i];
    }
    cout << endl;

    return 0;
}