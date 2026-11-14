import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Drones from "./pages/Drones.jsx";
import DroneDetail from "./pages/DroneDetail.jsx";
import Search from "./pages/Search.jsx";
import News from "./pages/News.jsx";
import Post from "./pages/Post.jsx";
import Contact from "./pages/Contact.jsx";
import QuoteView from "./pages/QuoteView.jsx";
import Login from "./pages/Login.jsx";
import Account from "./pages/Account.jsx";
import AccountLogin from "./pages/AccountLogin.jsx";
import Admin from "./pages/Admin.jsx";
import NotFound from "./pages/NotFound.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="drones" element={<Drones />} />
        <Route path="drones/:slug" element={<DroneDetail />} />
        <Route path="search" element={<Search />} />
        <Route path="news" element={<News />} />
        <Route path="news/:slug" element={<Post />} />
        <Route path="contact" element={<Contact />} />
        <Route path="quotes/:id" element={<QuoteView />} />
        <Route path="login" element={<Login />} />
        <Route path="account" element={<Account />} />
        <Route path="account/login" element={<AccountLogin />} />
        <Route path="admin" element={<Admin />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
