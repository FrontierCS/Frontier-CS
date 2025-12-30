#include <bits/stdc++.h>
using namespace std;

int main() {
    int sub, n;
    scanf("%d %d", &sub, &n);
    int f_b = min(100, n / 10);
    if (n <= 10) f_b = 1;
    vector<vector<int>> adj(n + 1);
    set<int> remaining_set;
    for (int i = 1; i <= n; ++i) remaining_set.insert(i);
    // Build independent set B
    vector<int> B;
    vector<int> candidates(n);
    for (int i = 0; i < n; ++i) candidates[i] = i + 1;
    for (int lab : candidates) {
        printf("1 %d\n", lab);
        fflush(stdout);
        int res;
        scanf("%d", &res);
        if (res == 0) {
            B.push_back(lab);
            if ((int)B.size() == f_b) break;
        } else {
            printf("1 %d\n", lab);
            fflush(stdout);
            int res2;
            scanf("%d", &res2);
        }
    }
    // Now S = B lit
    // Compute remaining
    vector<bool> in_B(n + 1, false);
    for (int b : B) in_B[b] = true;
    vector<int> rem_vec;
    for (int i = 1; i <= n; ++i) {
        if (!in_B[i]) {
            rem_vec.push_back(i);
            remaining_set.erase(i);
        }
    }
    // Batch to find Next
    int r_size = rem_vec.size();
    int Lbatch = 2 * r_size;
    printf("%d", Lbatch);
    for (int u : rem_vec) {
        printf(" %d %d", u, u);
    }
    printf("\n");
    fflush(stdout);
    vector<int> resbatch(Lbatch);
    for (int i = 0; i < Lbatch; ++i) {
        scanf("%d", &resbatch[i]);
    }
    vector<int> Next;
    for (int j = 0; j < r_size; ++j) {
        int idx = 2 * j + 1;
        if (resbatch[idx] == 1) {
            Next.push_back(rem_vec[j]);
        }
    }
    // Now S still B, turn off B
    int Lb = B.size();
    if (Lb > 0) {
        printf("%d", Lb);
        for (int b : B) printf(" %d", b);
        printf("\n");
        fflush(stdout);
        for (int i = 0; i < Lb; ++i) {
            int dummy;
            scanf("%d", &dummy);
        }
    }
    // S = empty
    // Now for each b find neigh in Next
    for (int b : B) {
        // add b
        printf("1 %d\n", b);
        fflush(stdout);
        int res0;
        scanf("%d", &res0);
        // batch Next
        int Ln = 2 * Next.size();
        printf("%d", Ln);
        for (int u : Next) {
            printf(" %d %d", u, u);
        }
        printf("\n");
        fflush(stdout);
        vector<int> resn(Ln);
        for (int i = 0; i < Ln; ++i) {
            scanf("%d", &resn[i]);
        }
        // find neigh
        for (size_t j = 0; j < Next.size(); ++j) {
            int idx = 2 * j + 1;
            if (resn[idx] == 1) {
                int u = Next[j];
                adj[b].push_back(u);
                adj[u].push_back(b);
            }
        }
        // remove b
        printf("1 %d\n", b);
        fflush(stdout);
        int res1;
        scanf("%d", &res1);
    }
    // Now initial induced on potential F = vertices with deg 1
    vector<int> potential_F;
    for (int i = 1; i <= n; ++i) {
        if ((int)adj[i].size() == 1) potential_F.push_back(i);
    }
    // induced on potential_F
    int pf_size = potential_F.size();
    for (int ee = 0; ee < pf_size; ++ee) {
        int e = potential_F[ee];
        // add e
        printf("1 %d\n", e);
        fflush(stdout);
        int res0;
        scanf("%d", &res0);
        // others
        vector<int> others;
        for (int jj = 0; jj < pf_size; ++jj) {
            if (jj != ee) others.push_back(potential_F[jj]);
        }
        int Lo = 2 * others.size();
        printf("%d", Lo);
        for (int o : others) {
            printf(" %d %d", o, o);
        }
        printf("\n");
        fflush(stdout);
        vector<int> reso(Lo);
        for (int i = 0; i < Lo; ++i) {
            scanf("%d", &reso[i]);
        }
        // find adj
        for (size_t j = 0; j < others.size(); ++j) {
            int idx = 2 * j + 1;
            if (reso[idx] == 1) {
                int o = others[j];
                bool has = false;
                for (int nb : adj[e]) {
                    if (nb == o) has = true;
                }
                if (!has) {
                    adj[e].push_back(o);
                    adj[o].push_back(e);
                }
            }
        }
        // remove e
        printf("1 %d\n", e);
        fflush(stdout);
        int resr;
        scanf("%d", &resr);
    }
    // Now loop
    while (!remaining_set.empty()) {
        // compute current_F = deg 1
        vector<int> current_F;
        for (int i = 1; i <= n; ++i) {
            if ((int)adj[i].size() == 1) current_F.push_back(i);
        }
        // induced on current_F
        int cf_size = current_F.size();
        for (int ee = 0; ee < cf_size; ++ee) {
            int e = current_F[ee];
            // add e
            printf("1 %d\n", e);
            fflush(stdout);
            int res0;
            scanf("%d", &res0);
            // others
            vector<int> others;
            for (int jj = 0; jj < cf_size; ++jj) {
                if (jj != ee) others.push_back(current_F[jj]);
            }
            int Lo = 2 * others.size();
            printf("%d", Lo);
            for (int o : others) {
                printf(" %d %d", o, o);
            }
            printf("\n");
            fflush(stdout);
            vector<int> reso(Lo);
            for (int i = 0; i < Lo; ++i) {
                scanf("%d", &reso[i]);
            }
            // find adj
            for (size_t j = 0; j < others.size(); ++j) {
                int idx = 2 * j + 1;
                if (reso[idx] == 1) {
                    int o = others[j];
                    bool has = false;
                    for (int nb : adj[e]) {
                        if (nb == o) has = true;
                    }
                    if (!has) {
                        adj[e].push_back(o);
                        adj[o].push_back(e);
                    }
                }
            }
            // remove e
            printf("1 %d\n", e);
            fflush(stdout);
            int resr;
            scanf("%d", &resr);
        }
        // recompute current_F = deg 1, now G
        current_F.clear();
        for (int i = 1; i <= n; ++i) {
            if ((int)adj[i].size() == 1) current_F.push_back(i);
        }
        int g_size = current_F.size();
        // set S = current_F
        if (g_size > 0) {
            printf("%d", g_size);
            for (int g : current_F) printf(" %d", g);
            printf("\n");
            fflush(stdout);
            for (int i = 0; i < g_size; ++i) {
                int dummy;
                scanf("%d", &dummy);
            }
        }
        // now S = G = current_F
        // batch
        rem_vec.assign(remaining_set.begin(), remaining_set.end());
        r_size = rem_vec.size();
        Lbatch = 2 * r_size;
        if (r_size > 0) {
            printf("%d", Lbatch);
            for (int u : rem_vec) {
                printf(" %d %d", u, u);
            }
            printf("\n");
            fflush(stdout);
            for (int i = 0; i < Lbatch; ++i) {
                int rb;
                scanf("%d", &rb);
                resbatch[i] = rb;
            }
            // Next
            Next.clear();
            for (int j = 0; j < r_size; ++j) {
                int idx = 2 * j + 1;
                if (resbatch[idx] == 1) {
                    int u = rem_vec[j];
                    Next.push_back(u);
                    remaining_set.erase(u);
                }
            }
        } else {
            Next.clear();
        }
        // now S still G
        // now per g matching
        int n_size = Next.size();
        for (int gg = 0; gg < g_size; ++gg) {
            int g = current_F[gg];
            // turn off others
            vector<int> to_off;
            for (int jj = 0; jj < g_size; ++jj) {
                if (jj != gg) to_off.push_back(current_F[jj]);
            }
            int Loff = to_off.size();
            if (Loff > 0) {
                printf("%d", Loff);
                for (int oo : to_off) printf(" %d", oo);
                printf("\n");
                fflush(stdout);
                for (int i = 0; i < Loff; ++i) {
                    int dummy;
                    scanf("%d", &dummy);
                }
            }
            // now S={g}
            // batch Next
            int Ln = 2 * n_size;
            printf("%d", Ln);
            for (int u : Next) {
                printf(" %d %d", u, u);
            }
            printf("\n");
            fflush(stdout);
            vector<int> resn(Ln);
            for (int i = 0; i < Ln; ++i) {
                scanf("%d", &resn[i]);
            }
            // find neigh
            for (size_t j = 0; j < Next.size(); ++j) {
                int idx = 2 * j + 1;
                if (resn[idx] == 1) {
                    int u = Next[j];
                    bool has = false;
                    for (int nb : adj[g]) {
                        if (nb == u) has = true;
                    }
                    if (!has) {
                        adj[g].push_back(u);
                        adj[u].push_back(g);
                    }
                }
            }
            // turn back to_off
            if (Loff > 0) {
                printf("%d", Loff);
                for (int oo : to_off) printf(" %d", oo);
                printf("\n");
                fflush(stdout);
                for (int i = 0; i < Loff; ++i) {
                    int dummy;
                    scanf("%d", &dummy);
                }
            }
            // now S=G again
        }
        // turn off G
        if (g_size > 0) {
            printf("%d", g_size);
            for (int g : current_F) printf(" %d", g);
            printf("\n");
            fflush(stdout);
            for (int i = 0; i < g_size; ++i) {
                int dummy;
                scanf("%d", &dummy);
            }
        }
        // S=empty
    }
    // Now build perm from 1
    vector<int> perm;
    int start = 1;
    int curr = start;
    int prevv = 0; // invalid
    set<int> visited;
    do {
        perm.push_back(curr);
        visited.insert(curr);
        int nextt = -1;
        for (int nb : adj[curr]) {
            if (nb != prevv) {
                nextt = nb;
                break;
            }
        }
        prevv = curr;
        curr = nextt;
        if (curr == 0) break; // error
    } while (curr != start);
    // if perm.size() != n or visited.size() !=n error, but assume correct
    // output
    printf("-1");
    for (int p : perm) {
        printf(" %d", p);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}