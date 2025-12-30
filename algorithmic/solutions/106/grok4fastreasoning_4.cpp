#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> colorr, parrent;

int queryy(const vector<int>& s) {
    if (s.empty()) return 0;
    cout << "? " << s.size() << endl;
    for (int x : s) cout << x << " ";
    cout << endl;
    cout.flush();
    int m;
    cin >> m;
    if (m == -1) exit(0);
    return m;
}

void get_path_to_root(int x, vector<int>& path) {
    while (x != -1) {
        path.push_back(x);
        x = parrent[x];
    }
}

vector<int> get_cycle(int u, int w, bool is_back) {
    vector<int> u_to_root, w_to_root;
    get_path_to_root(u, u_to_root);
    get_path_to_root(w, w_to_root);
    reverse(u_to_root.begin(), u_to_root.end()); // root to u
    reverse(w_to_root.begin(), w_to_root.end()); // root to w
    int com = 0;
    int minsz = min(u_to_root.size(), w_to_root.size());
    while (com < minsz && u_to_root[com] == w_to_root[com]) com++;
    if (com == 0) {
        // shouldn't happen
        assert(false);
    }
    int lca_idx = com - 1;
    int lcaa = u_to_root[lca_idx];
    // sub_u: lca to u
    vector<int> sub_u(u_to_root.begin() + lca_idx, u_to_root.end());
    // sub_w: lca to w
    vector<int> sub_w(w_to_root.begin() + lca_idx, w_to_root.end());
    // u to lca: reverse sub_u
    vector<int> u_to_lca = sub_u;
    reverse(u_to_lca.begin(), u_to_lca.end()); // u ... lca
    // lca to w without lca: sub_w[1:]
    vector<int> lca_to_w(sub_w.begin() + 1, sub_w.end()); // ... w
    // cycle: u_to_lca (u...lca) + lca_to_w (...w) + back to u via edge
    vector<int> cyclee = u_to_lca;
    cyclee.insert(cyclee.end(), lca_to_w.begin(), lca_to_w.end());
    // now last is w, add u? No, the order is u ... lca ... w , then edge w-u closes it.
    // But to list in order, say starting from u: u ... lca ... w u, but since cycle, list without last u.
    // But problem allows any order as long as consecutive edges.
    // But to have cl to c1.
    return cyclee;
}

int find_one_neighb(int startt, int endd, const vector<int>& plist, int uu) {
    if (startt + 1 == endd) {
        int vv = plist[startt];
        vector<int> pr = {uu, vv};
        int ep = queryy(pr);
        if (ep == 1) return vv;
        return -1;
    }
    int midd = (startt + endd) / 2;
    // left
    vector<int> subb(plist.begin() + startt, plist.begin() + midd);
    int esubb = queryy(subb);
    vector<int> usubb = subb;
    usubb.push_back(uu);
    int eusubb = queryy(usubb);
    int crosss = eusubb - esubb;
    if (crosss > 0) {
        int ress = find_one_neighb(startt, midd, plist, uu);
        if (ress != -1) return ress;
    }
    // right
    vector<int> subr(plist.begin() + midd, plist.begin() + endd);
    int esubr = queryy(subr);
    vector<int> usubr = subr;
    usubr.push_back(uu);
    int eusubr = queryy(usubr);
    int crossr = eusubr - esubr;
    if (crossr > 0) {
        int resr = find_one_neighb(midd, endd, plist, uu);
        if (resr != -1) return resr;
    }
    return -1;
}

int find_one_neighb(const vector<int>& poss, int uu) {
    return find_one_neighb(0, poss.size(), poss, uu);
}

int find_one_adj_to(const vector<int>& uu_list, const vector<int>& ll) {
    int el = queryy(ll);
    // similar to find_adj but return first one
    // implement recursive similar to below, but return when size1 and cross>0
    function<int(int, int, const vector<int>&)> rec = [&](int st, int en, const vector<int>& ulist) -> int {
        if (st + 1 == en) {
            int uuu = ulist[st];
            vector<int> luu = ll;
            luu.push_back(uuu);
            int eluu = queryy(luu);
            int cross = eluu - el;
            if (cross > 0) return uuu;
            return -1;
        }
        int md = (st + en) / 2;
        // left
        vector<int> leftt(ulist.begin() + st, ulist.begin() + md);
        int elef = queryy(leftt);
        vector<int> lulef = ll;
        for (int xx : leftt) lulef.push_back(xx);
        int elulef = queryy(lulef);
        int cl = elulef - el - elef;
        if (cl > 0) {
            int resl = rec(st, md, ulist);
            if (resl != -1) return resl;
        }
        // right
        vector<int> rightt(ulist.begin() + md, ulist.begin() + en);
        int erig = queryy(rightt);
        vector<int> lurig = ll;
        for (int xx : rightt) lurig.push_back(xx);
        int elurig = queryy(lurig);
        int cr = elurig - el - erig;
        if (cr > 0) {
            int resr = rec(md, en, ulist);
            if (resr != -1) return resr;
        }
        return -1;
    };
    return rec(0, uu_list.size(), uu_list);
}

pair<int, int> find_one_edg(const vector<int>& ss) {
    int sz = ss.size();
    if (sz == 2) {
        return {ss[0], ss[1]};
    }
    if (sz <= 3) {
        for (int i = 0; i < sz; ++i) {
            for (int j = i + 1; j < sz; ++j) {
                vector<int> prr = {ss[i], ss[j]};
                if (queryy(prr) == 1) return {ss[i], ss[j]};
            }
        }
        assert(false);
        return {-1, -1};
    }
    int md = sz / 2;
    vector<int> s1(ss.begin(), ss.begin() + md);
    vector<int> s2(ss.begin() + md, ss.end());
    int e1 = queryy(s1);
    if (e1 > 0) {
        return find_one_edg(s1);
    }
    int e2 = queryy(s2);
    if (e2 > 0) {
        return find_one_edg(s2);
    }
    // cross
    int u = find_one_adj_to(s1, s2);
    int v = find_one_neighb(s2, u);
    return {u, v};
}

void find_adjj(int e_ll, int stt, int enn, const vector<int>& ulistt, const vector<int>& llist, vector<int>& res) {
    if (stt + 1 == enn) {
        int uu = ulistt[stt];
        vector<int> lu = llist;
        lu.push_back(uu);
        int eluu = queryy(lu);
        int cross = eluu - e_ll;
        if (cross > 0) res.push_back(uu);
        return;
    }
    int mdd = (stt + enn) / 2;
    // left
    vector<int> leftt(ulistt.begin() + stt, ulistt.begin() + mdd);
    int elef = queryy(leftt);
    vector<int> lulef = llist;
    for (int xx : leftt) lulef.push_back(xx);
    int elulef = queryy(lulef);
    int cl = elulef - e_ll - elef;
    if (cl > 0) {
        find_adjj(e_ll, stt, mdd, ulistt, llist, res);
    }
    // right
    vector<int> rightt(ulistt.begin() + mdd, ulistt.begin() + enn);
    int erig = queryy(rightt);
    vector<int> lurig = llist;
    for (int xx : rightt) lurig.push_back(xx);
    int elurig = queryy(lurig);
    int cr = elurig - e_ll - erig;
    if (cr > 0) {
        find_adjj(e_ll, mdd, enn, ulistt, llist, res);
    }
}

int main() {
    cin >> n;
    colorr.assign(n + 1, -1);
    parrent.assign(n + 1, -1);
    colorr[1] = 0;
    parrent[1] = -1;
    vector<int> curr_layer = {1};
    while (!curr_layer.empty()) {
        int cc = colorr[curr_layer[0]];
        int next_cc = 1 - cc;
        vector<int> samee;
        for (int i = 1; i <= n; ++i) {
            if (colorr[i] == next_cc) samee.push_back(i);
        }
        int e_samee = queryy(samee);
        vector<int> uncol;
        for (int i = 1; i <= n; ++i) {
            if (colorr[i] == -1) uncol.push_back(i);
        }
        vector<int> next_lay;
        int e_curr = queryy(curr_layer);
        if (!uncol.empty()) {
            find_adjj(e_curr, 0, uncol.size(), uncol, curr_layer, next_lay);
        }
        // check back for each
        for (int uu : next_lay) {
            vector<int> suu = samee;
            suu.push_back(uu);
            int esuu = queryy(suu);
            int cross_s = esuu - e_samee;
            if (cross_s > 0) {
                // conflict back
                int ww = find_one_neighb(samee, uu);
                vector<int> cycl = get_cycle(uu, ww, true);
                cout << "N " << cycl.size() << endl;
                for (int vv : cycl) cout << vv << " ";
                cout << endl;
                cout.flush();
                return 0;
            }
        }
        // check internal
        int e_nextl = queryy(next_lay);
        if (e_nextl > 0) {
            // conflict intra
            pair<int, int> edg = find_one_edg(next_lay);
            int pp = edg.first, qq = edg.second;
            vector<int> cycl = get_cycle(pp, qq, false);
            cout << "N " << cycl.size() << endl;
            for (int vv : cycl) cout << vv << " ";
            cout << endl;
            cout.flush();
            return 0;
        }
        // assign
        for (int uu : next_lay) {
            colorr[uu] = next_cc;
            int ppar = find_one_neighb(curr_layer, uu);
            parrent[uu] = ppar;
        }
        curr_layer = next_lay;
    }
    // bipartite
    vector<int> part_0;
    for (int i = 1; i <= n; ++i) {
        if (colorr[i] == 0) part_0.push_back(i);
    }
    cout << "Y " << part_0.size() << endl;
    for (int x : part_0) cout << x << " ";
    cout << endl;
    cout.flush();
    return 0;
}