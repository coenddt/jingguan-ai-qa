/** 登录页（原型 login-page 1:1）：左蓝渐变品牌区（网格/粒子/光线动效）+ 右登录表单 */

import LoginForm from './LoginForm'

export default function Login() {
  return (
    <div className="login-page">
      <div className="login-left">
        <div className="bg-grid" />
        <div className="bg-particle" />
        <div className="bg-particle" />
        <div className="bg-particle" />
        <div className="bg-particle" />
        <div className="bg-particle" />
        <div className="bg-line" />
        <div className="bg-line" />
        <div className="bg-line" />
        <div className="logo-icon"><i className="fas fa-chart-line" /></div>
        <h1>经管之星·AI问数助手</h1>
        <p>自然语言进，text-to-query 出，结果直观可见</p>
      </div>
      <div className="login-right">
        <h2>欢迎回来</h2>
        <p className="sub">请登录您的账号</p>
        <LoginForm />
      </div>
    </div>
  )
}
