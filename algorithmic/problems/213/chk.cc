#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include "testlib.h"
#include <iostream>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <ctime>
#include <algorithm>

using namespace std;
static double referenceScore(double r) { return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r); }

const int N=202018,mod=1e9+7;
int cnt,root,top;
int siz[N],fix[N],val[N],c[N][2];
int b[N],stk[N];
mt19937 ran(time(0));
void updata(int x){
	siz[x]=siz[c[x][0]]+1+siz[c[x][1]];
}
inline int newnode(int x){
	val[++cnt]=x; fix[cnt]=1ll*ran()%mod*(ran()%mod)%mod;
	siz[cnt]=1; return cnt;
}
int merge(int A,int B){
	if(!A || !B)return A+B;
	if(fix[A]<fix[B])return c[A][1]=merge(c[A][1],B),updata(A),A;
	else return c[B][0]=merge(A,c[B][0]),updata(B),B;
}
void split(int now,int k,int &x,int &y){
	if(!now)x=y=0;
	else{
		if(siz[c[now][0]]<k)x=now,split(c[now][1],k-siz[c[now][0]]-1,c[now][1],y);
		else y=now,split(c[now][0],k,x,c[now][0]);
		updata(now);
	}
}
void dfs(int x){
	if(c[x][0])dfs(c[x][0]);
	stk[++top]=val[x];
	if(c[x][1])dfs(c[x][1]);
}
int read(){
	int x=0,f=1;char ch=getchar();
	while(ch<'0' || ch>'9'){if(ch=='-')f=-1;ch=getchar();}
	while(ch>='0' && ch<='9'){x=x*10+ch-'0';ch=getchar();}
	return x*f;
}
int main(int argc,char* argv[])
{
	registerTestlibCmd(argc,argv);
	int i,j,n,m,tot,x,y,z,T;
	n=inf.readInt();
	for(i=1;i<=n;i++)
		b[i]=inf.readInt();
	m=ouf.readInt();
	tot=ouf.readInt(0, 230*n, "operation count");
	T=tot;
	if(tot>230*n)
		quitf(_wa,"The number of your move is beyond acception");
	for(i=1;i<=n;i++)
		root=merge(root,newnode(b[i]));
	while(tot--){
		int u,v,x1,x2,x3,x4,x5;
		x=ouf.readInt(); y=ouf.readInt(); z=ouf.readInt();
		if(x>y) swap(x,y);
		if(y-x+1!=m || x<=0 || y>n || (z!=0 && z!=1))
			quitf(_wa,"Your answer is not legal");
		if(y==x){
			continue;
		}
		if(y==x+1){
			split(root,x-1,x1,x2);
			split(x2,1,x2,x3);
			split(x3,1,x3,x4);
			root=merge(x1,merge(x3,merge(x2,x4)));
		} else{
			split(root,x-1,x1,x2);
			split(x2,1,x2,x3);
			split(x3,y-x-1,x3,x4);
			split(x4,1,x4,x5);
			if(z)root=merge(x1,merge(x4,merge(x2,merge(x3,x5))));
			else root=merge(x1,merge(x3,merge(x4,merge(x2,x5))));
		}
	}
	dfs(root);
	for(i=1;i<=n;i++){
		if(stk[i]!=i)
			quitf(_wa,"Your answer is wrong %d %d",i,stk[i]);
	}

	// Calculate score based on number of operations
	// Operations count T ranges from optimal (around n) to maximum (23*n)
	// Score decreases linearly as T increases
	double baseline = 23.0 * n;  // Optimal number of operations
	double max_ops = 230.0 * n;  // Maximum acceptable operations

	// Calculate score (0.0 to 1.0)
	double performance = max(0.0, (max_ops - T) / (max_ops - baseline));
	double score_ratio = referenceScore(performance);
    score_ratio = natural_log_score(100.0L * (score_ratio), T, baseline, true) / 100.0;

	double unbounded_ratio = score_ratio;  // In this case, score is already bounded

	quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f", T, score_ratio, unbounded_ratio);

	return 0;
}
